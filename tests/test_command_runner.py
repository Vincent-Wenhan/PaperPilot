"""Tests for the safe command runner."""
from __future__ import annotations

from pathlib import Path
import unittest

from tools.command_runner import is_safe_command, run_command


class TestCommandRunner(unittest.TestCase):
    """Test command safety validation and execution."""

    def test_allow_python_version(self) -> None:
        safe, _ = is_safe_command("python --version")
        self.assertTrue(safe)

    def test_allow_pip_version(self) -> None:
        safe, _ = is_safe_command("pip --version")
        self.assertTrue(safe)

    def test_allow_entrypoint_help(self) -> None:
        safe, _ = is_safe_command("python train.py --help")
        self.assertTrue(safe)

    def test_block_rm_rf(self) -> None:
        safe, _ = is_safe_command("rm -rf /")
        self.assertFalse(safe)

    def test_block_sudo(self) -> None:
        safe, _ = is_safe_command("sudo rm -rf")
        self.assertFalse(safe)

    def test_block_curl(self) -> None:
        safe, _ = is_safe_command("curl http://example.com")
        self.assertFalse(safe)

    def test_block_shell_control_chars(self) -> None:
        safe, _ = is_safe_command("python --version; rm -rf /")
        self.assertFalse(safe)

    def test_block_pipe(self) -> None:
        safe, _ = is_safe_command("echo hello | grep h")
        self.assertFalse(safe)

    def test_block_not_in_allowlist(self) -> None:
        safe, _ = is_safe_command("pip install torch")
        self.assertFalse(safe)

    def test_empty_command_not_safe(self) -> None:
        safe, _ = is_safe_command("")
        self.assertFalse(safe)

    def test_run_valid_command(self) -> None:
        result = run_command("python --version", cwd=Path.cwd())
        self.assertEqual(result["returncode"], 0)
        self.assertIn("Python", result["stdout"])

    def test_run_invalid_cwd(self) -> None:
        result = run_command("python --version", cwd="/nonexistent/path")
        self.assertFalse(result["success"])
        self.assertIn("does not exist", result["stderr"])
