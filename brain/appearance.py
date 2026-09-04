"""Durable, model-safe choices for Tubby's visible appearance."""

import sqlite3
from pathlib import Path


EYE_COLORS = (
    "purple",
    "red",
    "amber",
    "yellow",
    "green",
    "teal",
    "cyan",
    "blue",
    "pink",
    "white",
)

CELEBRATIONS = ("gold", "rainbow")
WINK_EYES = ("left", "right")
DEFAULT_EYE_COLOR = "purple"

SCHEMA = """
CREATE TABLE IF NOT EXISTS robot_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class AppearanceStore:
    """The robot's global appearance settings, kept beside its memories."""

    DEFAULT_COLOR_KEY = "default_eye_color"

    def __init__(self, path: str | Path):
        self.path = str(path)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def default_eye_color(self) -> str:
        row = self.connection.execute(
            "SELECT value FROM robot_settings WHERE key = ?",
            (self.DEFAULT_COLOR_KEY,),
        ).fetchone()

        if row is None or row[0] not in EYE_COLORS:
            return DEFAULT_EYE_COLOR

        return row[0]

    def set_default_eye_color(self, color: str) -> None:
        if color not in EYE_COLORS:
            raise ValueError(f"Unknown eye color: {color}")

        self.connection.execute(
            "INSERT INTO robot_settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (self.DEFAULT_COLOR_KEY, color),
        )
        self.connection.commit()
