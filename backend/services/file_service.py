"""Read-only file browsing for generated workbench artifacts."""

from __future__ import annotations

from pathlib import Path

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
}
SKIP_PARTS = {"sandboxes", "__pycache__", ".pytest_cache"}


class FileService:
    def __init__(
        self,
        *,
        project_root: Path = PROJECT_ROOT,
        file_roots: list[Path] | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.file_roots = [
            Path(root).resolve()
            for root in (
                file_roots
                or [
                    WORKSPACE_DIR,
                    OUTPUTS_DIR,
                    PROJECT_ROOT / "generated_product",
                    PROJECT_ROOT / "examples" / "sample_outputs",
                ]
            )
        ]

    def _run_root(self, run_id: str) -> Path:
        return WORKSPACE_DIR / "runs" / run_id

    def _run_scoped_roots(self, run_id: str) -> list[Path]:
        run_root = self._run_root(run_id)
        return [run_root] + self.file_roots

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
