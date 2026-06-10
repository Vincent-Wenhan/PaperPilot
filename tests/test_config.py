"""Tests for configuration module."""
from __future__ import annotations

import unittest

from config import PROJECT_ROOT, OUTPUTS_DIR, MAIN_GOAL_DEBUG


class TestConfig(unittest.TestCase):
    """Test that config values are sensible."""

    def test_project_root_exists(self) -> None:
        self.assertTrue(PROJECT_ROOT.is_dir())

    def test_outputs_dir_is_subdirectory(self) -> None:
        self.assertTrue(str(OUTPUTS_DIR).startswith(str(PROJECT_ROOT)))

    def test_debug_goal_value(self) -> None:
        self.assertEqual(MAIN_GOAL_DEBUG, "debug errors")
