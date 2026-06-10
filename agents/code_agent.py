"""Agent for generating a minimal reproduction repository from paper evidence."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from agents.base_agent import BaseAgent
from config import WORKSPACE_DIR
from tools.llm_client import LLMClient


MAX_GENERATED_FILES = 20
MAX_GENERATED_CHARS = 500_000
FORBIDDEN_PATH_CHARACTERS = set('<>:"|?*')
RESERVED_GENERATED_PATHS = {"code_agent_manifest.json"}
WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


class CodeAgent(BaseAgent):
    """Generate and safely materialize a small paper-reproduction codebase."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        workspace_dir: str | Path = WORKSPACE_DIR,
    ) -> None:
        super().__init__(
            name="Code Agent",
            prompt_path="code_prompt.txt",
            llm_client=llm_client,
        )
        self.workspace_dir = Path(workspace_dir).expanduser().resolve()

    @staticmethod
    def _extract_bundle(raw_output: str) -> dict[str, Any]:
        text = raw_output.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Code Agent must return a JSON object.")
        try:
            bundle = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Code Agent returned invalid JSON: {exc}") from exc
        if not isinstance(bundle, dict):
            raise ValueError("Code Agent output must be a JSON object.")
        return bundle

    @staticmethod
    def _safe_relative_path(raw_path: object) -> PurePosixPath:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("Every generated file requires a non-empty path.")
        normalized = raw_path.strip().replace("\\", "/")
        relative = PurePosixPath(normalized)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe generated file path: {raw_path}")
        if not relative.parts or relative.parts[0].lower() == ".git":
            raise ValueError(f"Unsafe generated file path: {raw_path}")
        if relative.as_posix().lower() in RESERVED_GENERATED_PATHS:
            raise ValueError(f"Reserved generated file path: {raw_path}")
        for part in relative.parts:
            reserved_name = part.split(".", maxsplit=1)[0].lower()
            if (
                part in {"", ".", ".."}
                or any(character in FORBIDDEN_PATH_CHARACTERS for character in part)
                or part.endswith((" ", "."))
                or reserved_name in WINDOWS_RESERVED_NAMES
            ):
                raise ValueError(f"Unsafe generated file path: {raw_path}")
        return relative

    @classmethod
    def _validated_files(cls, bundle: dict[str, Any]) -> list[tuple[PurePosixPath, str]]:
        raw_files = bundle.get("files")
        if not isinstance(raw_files, list) or not raw_files:
            raise ValueError("Code Agent output must contain a non-empty files list.")
        if len(raw_files) > MAX_GENERATED_FILES:
            raise ValueError(
                f"Code Agent produced too many files ({len(raw_files)} > {MAX_GENERATED_FILES})."
            )

        files: list[tuple[PurePosixPath, str]] = []
        seen_paths: set[str] = set()
        total_chars = 0
        for item in raw_files:
            if not isinstance(item, dict):
                raise ValueError("Every generated file must be a JSON object.")
            relative = cls._safe_relative_path(item.get("path"))
            normalized_path = relative.as_posix().lower()
            if normalized_path in seen_paths:
                raise ValueError(f"Duplicate generated file path: {relative.as_posix()}")
            content = item.get("content")
            if not isinstance(content, str):
                raise ValueError(
                    f"Generated file content must be text: {relative.as_posix()}"
                )
            total_chars += len(content)
            if total_chars > MAX_GENERATED_CHARS:
                raise ValueError(
                    "Code Agent output exceeds the generated code size limit."
                )
            seen_paths.add(normalized_path)
            files.append((relative, content))
        return files

    @staticmethod
    def _mock_bundle() -> dict[str, Any]:
        return {
            "project_name": "paperpilot_mock_reproduction",
            "summary": (
                "Mock mode generated a safe placeholder project. Disable Mock Mode "
                "to let the configured model implement the paper method."
            ),
            "files": [
                {
                    "path": "README.md",
                    "content": (
                        "# Generated Reproduction Scaffold\n\n"
                        "This placeholder was created in Mock Mode. Disable Mock Mode "
                        "and run PaperPilot again to generate a paper-specific implementation.\n"
                    ),
                },
                {
                    "path": "main.py",
                    "content": (
                        '"""Minimal entry point generated by PaperPilot Mock Mode."""\n\n'
                        "import argparse\n\n\n"
                        "def main() -> None:\n"
                        '    parser = argparse.ArgumentParser(description="Generated reproduction scaffold")\n'
                        '    parser.add_argument("--smoke-test", action="store_true")\n'
                        "    args = parser.parse_args()\n"
                        "    if args.smoke_test:\n"
                        '        print("Mock reproduction smoke test passed.")\n\n\n'
                        'if __name__ == "__main__":\n'
                        "    main()\n"
                    ),
                },
                {
                    "path": "requirements.txt",
                    "content": "# Add paper-specific dependencies after disabling Mock Mode.\n",
                },
            ],
        }

    def generate_repository(self, input_data: dict[str, Any] | str) -> dict[str, Any]:
        """Generate a repository and return its path, summary, and file manifest."""
        if self.llm_client.mock_mode:
            bundle = self._mock_bundle()
        else:
            user_prompt = self._format_input(input_data)
            raw_output = self.llm_client.generate(self.system_prompt, user_prompt)
            bundle = self._extract_bundle(raw_output)

        files = self._validated_files(bundle)
        destination = self.workspace_dir / f"generated_reproduction_{uuid4().hex[:10]}"
        destination.mkdir(parents=True, exist_ok=False)

        written_files: list[str] = []
        for relative, content in files:
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written_files.append(relative.as_posix())

        summary = str(bundle.get("summary") or "Code Agent generated a reproduction project.")
        manifest = {
            "project_name": str(bundle.get("project_name") or destination.name),
            "summary": summary,
            "files": written_files,
        }
        (destination / "CODE_AGENT_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "repo_path": str(destination),
            **manifest,
        }

    def run(self, input_data: dict[str, Any] | str) -> str:
        """Generate a repository and return a printable summary."""
        try:
            generated = self.generate_repository(input_data)
            files = "\n".join(f"- `{path}`" for path in generated["files"])
            return (
                f"{generated['summary']}\n\n"
                f"Generated repository: `{generated['repo_path']}`\n\n"
                f"Files:\n{files}"
            )
        except Exception as exc:
            return f"{self.name} failed: {exc}"
