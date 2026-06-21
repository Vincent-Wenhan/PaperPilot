"""Artifact discovery and read helpers for workbench API endpoints."""

from __future__ import annotations

from pathlib import Path

from backend.schemas import ArtifactContent, ArtifactSummary
from config import OUTPUTS_DIR, PROJECT_ROOT, WORKSPACE_DIR
from tools.file_tools import read_file, resolve_allowed_path


ARTIFACT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".py",
    ".sh",
    ".yaml",
    ".yml",
    ".html",
    ".js",
    ".css",
}


class ArtifactService:
    def __init__(
        self,
        *,
        project_root: Path = PROJECT_ROOT,
        artifact_roots: list[Path] | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.artifact_roots = [
            Path(root).resolve()
            for root in (
                artifact_roots
                or [
                    OUTPUTS_DIR,
                    WORKSPACE_DIR / "runs",
                    PROJECT_ROOT / "examples" / "sample_outputs",
                    PROJECT_ROOT / "generated_product",
                ]
            )
        ]

    def list_artifacts(
        self,
        run_id: str = "latest",
        limit: int = 80,
        prefixes: list[str] | None = None,
    ) -> list[ArtifactSummary]:
        artifacts: list[ArtifactSummary] = []
        normalized_prefixes = [
            prefix.replace("\\", "/").strip("/").lower()
            for prefix in (prefixes or [])
            if prefix.strip()
        ]
        for root in self.artifact_roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if len(artifacts) >= limit:
                    return artifacts
                if not path.is_file() or path.suffix.lower() not in ARTIFACT_SUFFIXES:
                    continue
                relative = path.relative_to(self.project_root).as_posix()
                if normalized_prefixes and not any(
                    relative.lower().startswith(prefix)
                    for prefix in normalized_prefixes
                ):
                    continue
                artifacts.append(
                    ArtifactSummary(
                        artifact_id=relative,
                        run_id=run_id,
                        name=path.name,
                        kind=self._kind_for(path),
                        path=relative,
                        size_bytes=path.stat().st_size,
                    )
                )
        return artifacts

    def read_artifact(
        self,
        artifact_id: str,
        *,
        max_chars: int = 80_000,
    ) -> ArtifactContent:
        resolved = resolve_allowed_path(
            self.project_root / artifact_id,
            self.artifact_roots,
        )
        data = read_file(
            resolved,
            allowed_roots=self.artifact_roots,
            max_chars=max_chars,
        )
        return ArtifactContent(
            artifact_id=artifact_id,
            path=resolved.relative_to(self.project_root).as_posix(),
            content=str(data["content"]),
            truncated=bool(data["truncated"]),
        )

    @staticmethod
    def _kind_for(path: Path) -> str:
        name = path.name.lower()
        if name == "run.sh":
            return "runner"
        if "report" in name:
            return "report"
        if "plan" in name or "prd" in name or "spec" in name:
            return "plan"
        if path.suffix.lower() == ".py":
            return "code"
        return "artifact"


artifact_service = ArtifactService()
