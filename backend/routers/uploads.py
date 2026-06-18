"""PDF upload endpoint for the Workbench."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile

from config import PROJECT_ROOT

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOADS_DIR = PROJECT_ROOT / "uploads"


@router.post("/pdf")
async def upload_pdf(file: UploadFile) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    stem = "".join(
        c for c in Path(file.filename).stem if c.isalnum() or c in {"-", "_"}
    )[:80] or "paper"
    dest = UPLOADS_DIR / f"{uuid4().hex}_{stem}.pdf"
    dest.write_bytes(data)

    return {"pdf_path": str(dest)}
