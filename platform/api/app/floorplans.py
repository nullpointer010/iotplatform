"""Local filesystem storage for floor-plan images (ticket 0017).

Stored under MANUALS_DIR/floorplans/, keyed by sha256(site_area)[:32]
to keep ASCII-safe paths regardless of user input. Magic-byte check
enforces PNG / JPEG / WebP.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.manuals import MANUALS_DIR


FLOORPLANS_DIR = MANUALS_DIR / "floorplans"
MAX_BYTES = 10 * 1024 * 1024
CHUNK = 1024 * 1024

_CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "webp": "image/webp",
}


def _ensure_dir() -> None:
    FLOORPLANS_DIR.mkdir(parents=True, exist_ok=True)


def _key(site_area: str) -> str:
    return hashlib.sha256(site_area.encode("utf-8")).hexdigest()[:32]


def storage_key(site_area: str, ext: str) -> str:
    return f"{_key(site_area)}.{ext}"


def path_for(site_area: str, ext: str) -> Path:
    return FLOORPLANS_DIR / storage_key(site_area, ext)


def _detect_ext(first: bytes) -> str | None:
    if first.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if first.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if first.startswith(b"RIFF") and len(first) >= 12 and first[8:12] == b"WEBP":
        return "webp"
    return None


def content_type_for(ext: str) -> str:
    return _CONTENT_TYPES[ext]


async def _read_all_capped(upload: UploadFile) -> bytes:
    buf = bytearray()
    while True:
        chunk = await upload.read(CHUNK)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {MAX_BYTES} bytes",
            )
    return bytes(buf)


async def save_streaming(site_area: str, upload: UploadFile) -> tuple[int, str]:
    """Validate magic + size, write to disk, return (size_bytes, ext)."""
    _ensure_dir()
    data = await _read_all_capped(upload)
    ext = _detect_ext(data[:16])
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File is not a PNG, JPEG or WebP image",
        )
    target = path_for(site_area, ext)
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        with tmp.open("wb") as out:
            out.write(data)
        # Remove sibling extensions for this site so we never keep
        # two stale plans on disk after a format change.
        for other_ext in ("png", "jpg", "webp"):
            if other_ext == ext:
                continue
            other = path_for(site_area, other_ext)
            if other.exists():
                try:
                    other.unlink()
                except OSError:
                    pass
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return len(data), ext


def delete(site_area: str, ext: str) -> None:
    p = path_for(site_area, ext)
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass
