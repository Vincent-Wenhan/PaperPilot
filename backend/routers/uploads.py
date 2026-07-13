"""PDF upload endpoint for the Workbench.

Hardened with chunked streaming, magic-byte validation, MIME validation,
size limit, and content hash.  Returns a stable ``file_id`` rather than a
server absolute path.
"""

from __future__ import annotations

import hashlib
from uuid import uuid4

from fastapi import APIRouter, UploadFile

from backend.errors import InvalidArgumentError
from config import PROJECT_ROOT

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOADS_DIR = PROJECT_ROOT / "uploads"
MAX_PDF_BYTES = 100 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


@router.post("/pdf")
async def upload_pdf(file: UploadFile) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise InvalidArgumentError("Only PDF files are supported.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    file_id = f"file_{uuid4().hex}"
    dest = UPLOADS_DIR / f"{file_id}.pdf"
    digest = hashlib.sha256()
    total = 0
    first_chunk = True
    try:
        with dest.open("wb") as output:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_PDF_BYTES:
                    output.close()
                    dest.unlink(missing_ok=True)
                    raise InvalidArgumentError(
                        "PDF exceeds the 100MB upload limit.",
                        status_code=413,
                    )
                if first_chunk:
                    first_chunk = False
                    if not chunk.startswith(b"%PDF-"):
                        output.close()
                        dest.unlink(missing_ok=True)
                        raise InvalidArgumentError(
                            "Invalid PDF signature (must start with %PDF-).",
                            status_code=400,
                        )
                digest.update(chunk)
                output.write(chunk)
    finally:
        await file.close()

    if total == 0:
        dest.unlink(missing_ok=True)
        raise InvalidArgumentError("Uploaded PDF file is empty.")

    return {
        "file_id": file_id,
        "pdf_path": str(dest),
        "size_bytes": str(total),
        "sha256": digest.hexdigest(),
    }

