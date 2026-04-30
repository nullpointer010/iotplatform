"""Local filesystem storage for device manuals (ticket 0016).

Files are stored under MANUALS_DIR keyed by row UUID. The original
user-supplied filename never touches disk paths to avoid traversal /
collision issues.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status


MANUALS_DIR = Path(os.environ.get("MANUALS_DIR", "/var/lib/iot/manuals"))
MAX_BYTES = 10 * 1024 * 1024  # 10 MiB
PDF_MAGIC = b"%PDF-"
CHUNK = 1024 * 1024  # 1 MiB


def _ensure_dir() -> None:
    MANUALS_DIR.mkdir(parents=True, exist_ok=True)


def storage_key(file_id: UUID) -> str:
    return f"{file_id}.pdf"


def path_for(file_id: UUID) -> Path:
    return MANUALS_DIR / storage_key(file_id)


async def save_streaming(file_id: UUID, upload: UploadFile) -> int:
    """Stream upload to disk, enforcing PDF magic bytes + size cap.

    Returns the number of bytes written. Raises HTTPException(415) on
    non-PDF, HTTPException(413) on oversize.
    """
    _ensure_dir()
    target = path_for(file_id)
    tmp = target.with_suffix(".pdf.part")

    total = 0
    seen_magic = False
    try:
        with tmp.open("wb") as out:
            while True:
                chunk = await upload.read(CHUNK)
                if not chunk:
                    break
                if not seen_magic:
                    if not chunk.startswith(PDF_MAGIC):
                        raise HTTPException(
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail="File is not a PDF",
                        )
                    seen_magic = True
                total += len(chunk)
                if total > MAX_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds {MAX_BYTES} bytes",
                    )
                out.write(chunk)
        if not seen_magic:
            # zero-byte upload
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File is not a PDF",
            )
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return total


def delete(file_id: UUID) -> None:
    p = path_for(file_id)
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass
