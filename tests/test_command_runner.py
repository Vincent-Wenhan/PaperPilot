"""Tests for the safe command runner."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.command_runner import (
    assess_risk,
    is_safe_command,
    run_command,
    run_sandbox_verification,
)


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

    def test_entrypoint_help_is_low_risk(self) -> None:
        risk_level, reason = assess_risk("python train.py --help")
        self.assertEqual(risk_level, "low")
        self.assertIn("Help flag", reason)

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

    def test_sandbox_verification_skips_empty_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "requirements.txt").write_text(
                "# No dependencies for this generated smoke test.\n",
                encoding="utf-8",
            )
            (root / "main.py").write_text(
                "import argparse\n\n"
                "def main() -> None:\n"
                "    parser = argparse.ArgumentParser()\n"
                "    parser.add_argument('--smoke-test', action='store_true')\n"
                "    parser.parse_args()\n"
                "    print('ok')\n\n"
                "if __name__ == '__main__':\n"
                "    main()\n",
                encoding="utf-8",
            )

            result = run_sandbox_verification(
                root,
                smoke_test_command="python main.py --smoke-test",
            )

        pip_step = next(item for item in result["results"] if item["step"] == "pip install")
        self.assertTrue(pip_step["passed"])
        self.assertIn("Skipped", pip_step["stdout"])
        self.assertTrue(result["passed"])
