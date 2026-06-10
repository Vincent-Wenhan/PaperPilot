"""Tests for repository scanner."""
from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from tools.repo_scanner import scan_repo


class TestRepoScanner(unittest.TestCase):
    """Test repository scanning logic."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Create sample repo files
        (self.root / "README.md").write_text("# Test Repo")
        (self.root / "requirements.txt").write_text("torch>=2.0")
        (self.root / "train.py").write_text("def main(): pass")
        (self.root / "config.yaml").write_text("data: test")
        (self.root / "notebooks").mkdir()
        (self.root / "notebooks" / "demo.ipynb").write_text("{}")
        # A file that should be skipped
        (self.root / "__pycache__").mkdir()
        (self.root / "__pycache__" / "cache.py").write_text("")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_scanner_finds_important_files(self) -> None:
        result = scan_repo(str(self.root))
        self.assertIn("README.md", result["important_files"])
        self.assertIn("requirements.txt", result["important_files"])

    def test_scanner_detects_entrypoints(self) -> None:
        result = scan_repo(str(self.root))
        self.assertIn("train.py", result["possible_entrypoints"])

    def test_scanner_skips_pycache(self) -> None:
        result = scan_repo(str(self.root))
        all_files = result["important_files"]
        self.assertNotIn("__pycache__/cache.py", all_files)

    def test_scanner_detects_config_files(self) -> None:
        result = scan_repo(str(self.root))
        self.assertTrue(
            any("config.yaml" in f for f in result["config_files"]),
        )

    def test_scanner_detects_important_directories(self) -> None:
        result = scan_repo(str(self.root))
        self.assertIn("notebooks", result["important_directories"])

    def test_scanner_raises_on_nonexistent_dir(self) -> None:
        with self.assertRaises(NotADirectoryError):
            scan_repo("/nonexistent/path/12345")
