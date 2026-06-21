"""Patch-first editing helpers for generated code and products."""

from __future__ import annotations

import difflib
import py_compile
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from backend.schemas import PatchApplyResult, PatchProposal, PatchProposeRequest
from config import PROJECT_ROOT, WORKSPACE_DIR
from tools.file_tools import resolve_allowed_path


class PatchService:
    """Generate and apply reviewed patches inside generated-code roots only.

    Patch lifecycle:
      propose → PendingAction → approve → apply → syntax_check → event
    """

    def __init__(
        self,
        *,
        project_root: Path = PROJECT_ROOT,
        patch_roots: list[Path] | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.patch_roots = [
            Path(root).resolve()
            for root in (
                patch_roots
                or [
                    WORKSPACE_DIR,
                    PROJECT_ROOT / "generated_product",
                ]
            )
        ]
        self._patches: dict[str, PatchProposal] = {}

    def list_patches(self, run_id: str = "") -> list[PatchProposal]:
        matches = [
            p for p in self._patches.values()
            if not run_id or p.run_id == run_id
        ]
        return [deepcopy(p) for p in matches]

    def propose_patch(
        self,
        run_id: str,
        request: PatchProposeRequest,
    ) -> PatchProposal:
        resolved = resolve_allowed_path(
            self.project_root / request.path,
            self.patch_roots,
            allow_missing=True,
        )
        old_content = ""
        if resolved.exists():
            if not resolved.is_file():
                raise ValueError(f"Patch target is not a file: {resolved}")
            old_content = resolved.read_text(encoding="utf-8", errors="replace")
        diff = "".join(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                request.new_content.splitlines(keepends=True),
                fromfile=f"a/{request.path}",
                tofile=f"b/{request.path}",
            )
        )
        patch = PatchProposal(
            patch_id=f"patch_{uuid4().hex[:12]}",
            run_id=run_id,
            path=resolved.relative_to(self.project_root).as_posix(),
            old_content=old_content,
            new_content=request.new_content,
            unified_diff=diff,
            reason=request.reason,
        )
        self._patches[patch.patch_id] = patch
        return deepcopy(patch)

    def apply_patch(self, patch_id: str) -> PatchApplyResult | None:
        patch = self._patches.get(patch_id)
        if patch is None:
            return None
        resolved = resolve_allowed_path(
            self.project_root / patch.path,
            self.patch_roots,
            allow_missing=True,
        )
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(patch.new_content, encoding="utf-8")
        check_ok, check_msg = self._syntax_check(resolved)
        updated = patch.model_copy(update={"status": "applied"})
        self._patches[patch_id] = updated
        message = "Patch applied to generated workspace file."
        if check_ok:
            message += " Syntax check passed."
        else:
            message += f" Syntax check warning: {check_msg}"
        return PatchApplyResult(
            patch_id=patch_id,
            path=patch.path,
            applied=True,
            message=message,
            syntax_ok=check_ok,
            syntax_failures=[] if check_ok else [
                {"path": patch.path, "error": check_msg}
            ],
        )

    def get_patch(self, patch_id: str) -> PatchProposal | None:
        patch = self._patches.get(patch_id)
        return deepcopy(patch) if patch else None

    def _syntax_check(self, resolved: Path) -> tuple[bool, str]:
        if resolved.suffix != ".py":
            return True, ""
        try:
            py_compile.compile(str(resolved), doraise=True)
            return True, ""
        except py_compile.PyCompileError as exc:
            return False, exc.msg
        except (OSError, SyntaxError) as exc:
            return False, str(exc)


patch_service = PatchService()
