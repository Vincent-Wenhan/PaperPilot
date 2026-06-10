"""Helpers for writing generated Markdown and shell script artifacts."""

from __future__ import annotations

from pathlib import Path


def save_markdown(content: str, path: str | Path) -> None:
    """Save UTF-8 Markdown content, creating parent directories as needed."""
    output_path = Path(path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def save_shell_script(content: str, path: str | Path) -> None:
    """Save an executable Bash script with the required safety preamble."""
    output_path = Path(path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    body = content
    if body.startswith("#!"):
        body = "\n".join(body.splitlines()[1:])
    body = body.lstrip("\n")
    if body.startswith("set -e"):
        body = "\n".join(body.splitlines()[1:]).lstrip("\n")

    script = "#!/usr/bin/env bash\nset -e\n"
    if body:
        script += f"\n{body.rstrip()}\n"
    output_path.write_text(script, encoding="utf-8")
    output_path.chmod(output_path.stat().st_mode | 0o111)
