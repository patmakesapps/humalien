"""A chosen default eye color survives a restart and stays model-safe."""

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from appearance import AppearanceStore, DEFAULT_EYE_COLOR


class AppearanceStoreTests(unittest.TestCase):
    def test_the_factory_default_is_purple(self):
        with tempfile.TemporaryDirectory() as folder:
            store = AppearanceStore(Path(folder) / "robot.db")
            self.assertEqual(store.default_eye_color(), DEFAULT_EYE_COLOR)
            store.close()

    def test_a_default_survives_reopening_the_database(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "robot.db"
            first = AppearanceStore(database)
            first.set_default_eye_color("green")
            first.close()

            second = AppearanceStore(database)
            self.assertEqual(second.default_eye_color(), "green")
            second.close()

    def test_an_unknown_color_is_never_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            store = AppearanceStore(Path(folder) / "robot.db")

            with self.assertRaises(ValueError):
                store.set_default_eye_color("infrared")

            self.assertEqual(store.default_eye_color(), DEFAULT_EYE_COLOR)
            store.close()


if __name__ == "__main__":
    unittest.main()
