import json
import unittest

from tool_registry import ToolError, ToolRegistry


class ToolRegistryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.registry = ToolRegistry()

        @self.registry.tool(
            "greet",
            "Say hello to somebody.",
            properties={
                "name": {"type": "string"},
                "times": {"type": "integer", "minimum": 1, "maximum": 3},
                "mood": {"type": "string", "enum": ["warm", "flat"]},
            },
            required=["name"],
        )
        async def greet(robot, name, times=1, mood="warm"):
            return {"said": f"{mood} hello to {name}", "times": times}

        @self.registry.tool("explode", "Always fails.")
        async def explode(robot):
            raise RuntimeError("boom")

    async def run_tool(self, name, arguments=None):
        return json.loads(await self.registry.execute(None, name, arguments))

    async def test_definitions_match_the_realtime_shape(self):
        definition = self.registry.definitions()[0]

        self.assertEqual(definition["type"], "function")
        self.assertEqual(definition["name"], "greet")
        self.assertTrue(definition["description"])
        self.assertEqual(definition["parameters"]["type"], "object")
        self.assertEqual(definition["parameters"]["required"], ["name"])

    async def test_a_tool_runs(self):
        result = await self.run_tool("greet", '{"name": "Pat"}')

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["said"], "warm hello to Pat")

    async def test_registering_a_name_twice_is_refused(self):
        with self.assertRaises(ValueError):

            @self.registry.tool("greet", "A second greet.")
            async def greet_again(robot):
                return {}

    async def test_unknown_tool_fails_cleanly(self):
        result = await self.run_tool("dance")

        self.assertFalse(result["success"])
        self.assertIn("dance", result["error"])

    async def test_missing_required_input_tells_the_model_what_is_missing(self):
        result = await self.run_tool("greet", "{}")

        self.assertFalse(result["success"])
        self.assertIn("name", result["error"])

    async def test_unparseable_arguments_fail_rather_than_run_empty(self):
        result = await self.run_tool("greet", "not json")

        self.assertFalse(result["success"])

    async def test_missing_arguments_are_treated_as_none(self):
        result = await self.run_tool("explode", None)

        # Reached the handler, so empty arguments parsed rather than errored.
        self.assertFalse(result["success"])
        self.assertIn("boom", result["error"])

    async def test_a_number_sent_as_a_string_is_coerced(self):
        # Models do this constantly and it should not be a failure.
        result = await self.run_tool("greet", '{"name": "Pat", "times": "2"}')

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["times"], 2)

    async def test_a_value_that_cannot_be_coerced_is_rejected(self):
        result = await self.run_tool("greet", '{"name": "Pat", "times": "soon"}')

        self.assertFalse(result["success"])
        self.assertIn("times", result["error"])

    async def test_enum_is_enforced(self):
        result = await self.run_tool("greet", '{"name": "Pat", "mood": "smug"}')

        self.assertFalse(result["success"])
        self.assertIn("mood", result["error"])

    async def test_bounds_are_enforced(self):
        result = await self.run_tool("greet", '{"name": "Pat", "times": 9}')

        self.assertFalse(result["success"])
        self.assertIn("at most", result["error"])

    async def test_a_raising_tool_reports_failure_not_success(self):
        # The contract that matters: a tool that broke must never come back
        # looking like a tool that worked.
        result = await self.run_tool("explode")

        self.assertFalse(result["success"])
        self.assertNotIn("data", result)

    async def test_a_tool_error_reaches_the_model_verbatim(self):
        @self.registry.tool("blind", "Cannot see.")
        async def blind(robot):
            raise ToolError("There is no camera.")

        result = await self.run_tool("blind")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "There is no camera.")


if __name__ == "__main__":
    unittest.main()
