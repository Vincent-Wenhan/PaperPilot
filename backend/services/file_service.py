"""Read-only file browsing for generated workbench artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from backend.schemas import FileContent, FileNode
from config import OUTPUTS_DIR, PROJECT_ROOT, WORKSPACE_DIR
from tools.file_tools import read_file, resolve_allowed_path


VISIBLE_SUFFIXES = {
    ".md",
    ".py",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".sh",
    ".toml",
    ".html",
    ".js",
    ".css",
}
SKIP_PARTS = {"sandboxes", "__pycache__", ".pytest_cache"}


class FileService:
    def __init__(
        self,
        *,
        project_root: Path = PROJECT_ROOT,
        file_roots: list[Path] | None = None,
        run_root_resolver: Callable[[str], list[str | Path]] | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self._run_root_resolver = run_root_resolver
        self.file_roots = [
            Path(root).resolve()
            for root in (
                file_roots
                or [
                    WORKSPACE_DIR,
                    OUTPUTS_DIR,
                    WORKSPACE_DIR / "runs",
                    PROJECT_ROOT / "generated_product",
                    PROJECT_ROOT / "examples" / "sample_outputs",
                ]
            )
        ]

    def _run_root(self, run_id: str) -> Path:
        return WORKSPACE_DIR / "runs" / run_id

    def _run_scoped_roots(self, run_id: str) -> list[Path]:
        if run_id == "run_mock_reproduce":
            return self.file_roots

        candidates: list[str | Path] = []
        if self._run_root_resolver is not None:
            candidates.extend(self._run_root_resolver(run_id))
        else:
            candidates.extend(self._roots_from_run_service(run_id))

        run_root = self._run_root(run_id)
        if run_root.exists():
            candidates.append(run_root)

        roots: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            root = self._resolve_project_path(candidate)
            if root is None:
                continue
            key = root.as_posix().lower()
            if key in seen:
                continue
            seen.add(key)
            roots.append(root)
        return roots

    def _roots_from_run_service(self, run_id: str) -> list[str | Path]:
        from backend.services.run_service import run_service

        run = run_service.get_run(run_id)
        result = run_service.get_result(run_id) or {}
        roots: list[str | Path] = []
        if run is not None:
            summary = run.result_summary or {}
            roots.extend(
                self._path_values(
                    summary,
                    "generated_code_output_dir",
                    "reproduce_output_dir",
                    "product_output_dir",
                )
            )
        roots.extend(
            self._path_values(
                result,
                "generated_repo_path",
                "generated_code_output_dir",
                "reproduce_output_dir",
                "product_output_dir",
            )
        )

        output_files = result.get("output_files")
        if isinstance(output_files, dict):
            for value in output_files.values():
                raw_path = str(value or "").strip()
                if raw_path:
                    roots.append(Path(raw_path).parent)

        for action in run_service.list_actions(run_id):
            cwd = str(action.cwd or "").strip()
            if cwd:
                roots.append(cwd)
        return roots

    @staticmethod
    def _path_values(payload: dict[str, object], *keys: str) -> list[str]:
        values: list[str] = []
        for key in keys:
            value = str(payload.get(key) or "").strip()
            if value:
                values.append(value)
        return values

    def _resolve_project_path(self, raw_path: str | Path) -> Path | None:
        path = Path(raw_path).expanduser()
        resolved = path.resolve() if path.is_absolute() else (self.project_root / path).resolve()
        try:
            resolved.relative_to(self.project_root)
        except ValueError:
            return None
        return resolved

    def list_files(self, run_id: str = "", limit: int = 200) -> list[FileNode]:
        roots = self._run_scoped_roots(run_id) if run_id else self.file_roots
        nodes: list[FileNode] = []
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if len(nodes) >= limit:
                    return nodes
                if path.is_dir():
                    continue
                relative_parts = path.relative_to(root).parts
                if any(part in SKIP_PARTS for part in relative_parts):
                    continue
                if path.suffix.lower() not in VISIBLE_SUFFIXES:
                    continue
                relative = path.relative_to(self.project_root).as_posix()
                nodes.append(
                    FileNode(
                        path=relative,
                        name=path.name,
                        kind="file",
                        size_bytes=path.stat().st_size,
                    )
                )
        return nodes

    def read_content(self, path: str, run_id: str = "", max_chars: int = 80_000) -> FileContent:
        roots = self._run_scoped_roots(run_id) if run_id else self.file_roots
        resolved = resolve_allowed_path(
            self.project_root / path,
            roots,
        )
        data = read_file(
            resolved,
            allowed_roots=roots,
            max_chars=max_chars,
        )
        return FileContent(
            path=resolved.relative_to(self.project_root).as_posix(),
            content=str(data["content"]),
            truncated=bool(data["truncated"]),
        )


file_service = FileService()
