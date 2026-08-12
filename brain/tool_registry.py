"""What Humalien can do, declared once.

A tool's schema and its handler live together, so there is nothing to keep
in sync and no way to ship a tool the model can call but nothing answers.

Everything a tool returns goes back as one shape: a success with data, or a
failure with a message the model can act on. A tool that fails must never
look like a tool that worked and happened to mention an error.
"""

import json

JSON_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


class ToolError(Exception):
    """A failure the model should be told about plainly, and can correct."""


def _coerce(value, expected: str):
    """Forgive the mistakes models actually make: '5' for 5, 'yes' for true."""

    if not isinstance(value, str):
        return value, False

    text = value.strip()

    if expected == "integer":
        try:
            return int(text), True
        except ValueError:
            return value, False

    if expected == "number":
        try:
            return float(text), True
        except ValueError:
            return value, False

    if expected == "boolean":
        if text.lower() in ("true", "yes", "1"):
            return True, True
        if text.lower() in ("false", "no", "0"):
            return False, True

    return value, False


class ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, dict] = {}

    def tool(
        self,
        name: str,
        description: str,
        *,
        properties: dict | None = None,
        required: list[str] | None = None,
    ):
        """Register a handler along with the schema the model sees."""

        def register(handler):
            if name in self.tools:
                raise ValueError(f"Tool {name!r} is already registered")

            self.tools[name] = {
                "name": name,
                "description": description,
                "schema": {
                    "type": "object",
                    "properties": properties or {},
                    "required": required or [],
                },
                "handler": handler,
            }
            return handler

        return register

    def definitions(self) -> list[dict]:
        """The session.tools payload for the Realtime API."""

        return [
            {
                "type": "function",
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["schema"],
            }
            for tool in self.tools.values()
        ]

    @staticmethod
    def parse_arguments(raw) -> dict:
        """Arguments arrive as a JSON string, and occasionally as nonsense."""

        if raw is None or raw == "":
            return {}

        if isinstance(raw, dict):
            return raw

        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raise ToolError("Arguments were not valid JSON.")

        if not isinstance(parsed, dict):
            raise ToolError("Arguments must be a JSON object.")

        return parsed

    @staticmethod
    def validate(arguments: dict, schema: dict) -> dict:
        """Check against the declared schema, coercing what is safe to coerce.

        Failures are phrased for the model, not for a log, because it gets
        to try again.
        """

        for field in schema.get("required", []):
            if arguments.get(field) in (None, ""):
                raise ToolError(f"Missing required input: {field}")

        for key, value in list(arguments.items()):
            spec = schema.get("properties", {}).get(key)

            if not isinstance(spec, dict) or value is None:
                continue

            expected = spec.get("type")

            if expected in JSON_TYPES:
                # bool is a subclass of int, so True must not pass as a number.
                correct = isinstance(value, JSON_TYPES[expected]) and not (
                    expected in ("integer", "number") and isinstance(value, bool)
                )

                if not correct:
                    value, coerced = _coerce(value, expected)

                    if not coerced:
                        raise ToolError(
                            f"Invalid type for '{key}': expected {expected}, "
                            f"got {type(arguments[key]).__name__}"
                        )

                    arguments[key] = value

            allowed = spec.get("enum")

            if isinstance(allowed, list) and allowed and value not in allowed:
                options = ", ".join(repr(option) for option in allowed)
                raise ToolError(f"Invalid value for '{key}': must be one of {options}")

            if expected in ("integer", "number"):
                minimum, maximum = spec.get("minimum"), spec.get("maximum")

                if minimum is not None and value < minimum:
                    raise ToolError(f"'{key}' must be at least {minimum}")

                if maximum is not None and value > maximum:
                    raise ToolError(f"'{key}' must be at most {maximum}")

        return arguments

    async def execute(self, robot, name: str, raw_arguments) -> str:
        """Run a tool and return the JSON the model will read."""

        tool = self.tools.get(name)

        if tool is None:
            return failure(f"There is no tool called {name}.")

        try:
            arguments = self.parse_arguments(raw_arguments)
            arguments = self.validate(arguments, tool["schema"])

            return success(await tool["handler"](robot, **arguments))

        except ToolError as error:
            return failure(str(error))

        except TypeError as error:
            # Almost always a handler signature that no longer matches its
            # schema, which is a bug rather than something the model can fix.
            return failure(f"{name} could not be called: {error}")

        except Exception as error:
            return failure(f"{type(error).__name__}: {error}")


def success(data) -> str:
    return json.dumps({"success": True, "data": data})


def failure(message: str) -> str:
    return json.dumps({"success": False, "error": message})
