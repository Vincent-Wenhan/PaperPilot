"""Shared Streamlit UI helpers."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

from config import PROJECT_ROOT
from pipeline.output_paths import resolve_output_file
from pipeline.stage_tracker import STAGE_DISPLAY_NAMES, stage_badge_label

UPLOADS_DIR = PROJECT_ROOT / "uploads"

OUTPUT_FILES = (
    ("reproduction_plan.md", "Download reproduction_plan.md", "text/markdown"),
    ("run.sh", "Download run.sh", "text/x-shellscript"),
    ("report.md", "Download report.md", "text/markdown"),
)
RUNNER_ENTRYPOINTS = (
    "train.py", "main.py", "eval.py", "test.py", "demo.py", "examples/demo.py",
)

def save_uploaded_pdf(uploaded_file: BinaryIO) -> Path:
    """Save one uploaded PDF under the project-local uploads directory."""
    original_name = Path(getattr(uploaded_file, "name", "paper.pdf")).name
    if Path(original_name).suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    data = uploaded_file.getvalue()
    if not data:
        raise ValueError("Uploaded PDF file is empty.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_stem = "".join(
        character
        for character in Path(original_name).stem
        if character.isalnum() or character in {"-", "_"}
    )[:80]
    safe_stem = safe_stem or "paper"
    destination = UPLOADS_DIR / f"{uuid4().hex}_{safe_stem}.pdf"
    destination.write_bytes(data)
    return destination


def show_pipeline_errors(
    errors: list[str],
    pipeline_status: str = "complete",
) -> None:
    if not errors:
        st.success("Analysis complete. No errors recorded.")
        return
    if pipeline_status == "failed":
        st.error(
            "LLM analysis failed. The visible outputs are fallback placeholders, "
            "not a real reading of the paper."
        )
    else:
        st.warning("Analysis completed, but some steps encountered issues:")
    for error in errors:
        st.error(error)


def build_generated_code_zip(repo_path: str, files: list[str]) -> bytes:
    """Build an in-memory ZIP from the validated generated-file manifest."""
    root = Path(repo_path).expanduser().resolve()
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for filename in files:
            path = (root / filename).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"Generated file is outside repository: {filename}") from exc
            if path.is_file():
                archive.write(path, arcname=filename)
        manifest = root / "CODE_AGENT_MANIFEST.json"
        if manifest.is_file():
            archive.write(manifest, arcname=manifest.name)
    return buffer.getvalue()


def show_outputs(result: dict[str, Any]) -> None:
    st.header("Output")
    show_pdf_quality_warnings(result)
    show_stage_provenance(result)
    tabs = st.tabs(
        [
            "Paper Summary",
            "Method Breakdown",
            "Code / Repository",
            "Environment Setup",
            "Experiment Plan",
            "run.sh",
            "report.md",
        ]
    )
    with tabs[0]:
        paper_context = result.get("paper_context") or {}
        if paper_context:
            st.caption(
                "PDF context sent to Research Understanding Agent: "
                f"{paper_context.get('characters', 0):,} characters across "
                f"{paper_context.get('pages', 0)} page(s); "
                f"truncated: {paper_context.get('truncated', False)}"
            )
        st.markdown(result.get("paper_info") or "Paper summary not yet generated.")
    with tabs[1]:
        st.markdown(result.get("method_info") or "Method breakdown not yet generated.")
    with tabs[2]:
        repo_path = result.get("repo_path")
        repo_source = result.get("repo_source")
        generated_repo_path = result.get("generated_repo_path")
        if repo_source:
            st.caption(f"Code source: {repo_source}")
        if repo_path:
            st.caption(f"Local repository: {repo_path}")
        if generated_repo_path:
            st.caption(f"Generated reproduction repository: {generated_repo_path}")
        implementation_model = result.get("implementation_model")
        if implementation_model:
            st.caption(f"Implementation model: {implementation_model}")
        code_info = result.get("code_info")
        if code_info:
            st.subheader("Additional Code Context")
            st.markdown(code_info)
        generated_files = result.get("generated_files") or []
        if generated_repo_path and generated_files:
            st.subheader("Generated Code")
            st.download_button(
                label="Download generated reproduction code",
                data=build_generated_code_zip(generated_repo_path, generated_files),
                file_name="paperpilot_generated_reproduction.zip",
                mime="application/zip",
                key="download_generated_reproduction",
            )
            generated_root = Path(generated_repo_path)
            for filename in generated_files:
                path = generated_root / filename
                if path.is_file():
                    with st.expander(filename):
                        language = "python" if path.suffix == ".py" else "text"
                        st.code(path.read_text(encoding="utf-8"), language=language)
        st.subheader("Repository Analysis")
        st.markdown(result.get("repo_info") or "Repository analysis not yet generated.")
    with tabs[3]:
        st.markdown(result.get("env_plan") or "Environment setup not yet generated.")
    with tabs[4]:
        st.markdown(result.get("experiment_plan") or "Experiment plan not yet generated.")
    with tabs[5]:
        st.code(result.get("run_sh") or "run.sh not yet generated.", language="bash")
    with tabs[6]:
        st.markdown(result.get("report") or "report.md not yet generated.")


def show_stage_provenance(result: dict[str, Any]) -> None:
    """Show whether each agent stage used real, fallback, or mock output."""
    sources = result.get("stage_sources") or {}
    if not sources:
        return
    st.subheader("Stage Provenance")
    columns = st.columns(min(len(sources), 4) or 1)
    for index, (stage_key, source) in enumerate(sources.items()):
        label = STAGE_DISPLAY_NAMES.get(stage_key, stage_key.replace("_", " ").title())
        badge = stage_badge_label(str(source))
        with columns[index % len(columns)]:
            if source == "real":
                st.success(f"{label}: {badge}")
            elif source == "fallback":
                st.warning(f"{label}: {badge}")
            else:
                st.info(f"{label}: {badge}")


def show_pdf_quality_warnings(result: dict[str, Any]) -> None:
    quality = result.get("pdf_quality") or {}
    if not quality:
        return
    if quality.get("is_scanned"):
        st.warning(
            "This PDF looks like a scanned document (low text density). "
            "PaperPilot will attempt OCR when Tesseract is available."
        )
    for warning in quality.get("warnings", []):
        st.warning(str(warning))


def show_downloads(result: dict[str, Any] | None = None) -> None:
    st.subheader("Download Output Files")
    output_dir = resolve_output_dir(result)
    if result and result.get("paper_name"):
        st.caption(f"Output directory: `{output_dir}`")
    columns = st.columns(len(OUTPUT_FILES))
    for column, (filename, label, mime) in zip(
        columns,
        OUTPUT_FILES,
        strict=True,
    ):
        path = resolve_output_file(result, filename)
        with column:
            if path.is_file():
                st.download_button(
                    label=label,
                    data=path.read_bytes(),
                    file_name=filename,
                    mime=mime,
                    key=f"download_{filename}",
                )
            else:
                st.info(f"{filename} not yet generated.")


