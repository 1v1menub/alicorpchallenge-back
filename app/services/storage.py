import uuid

import httpx

from app.core.config import settings

_MIME_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}


def _config() -> tuple[str, str, str]:
    if not (settings.supabase_url and settings.supabase_service_key):
        raise RuntimeError(
            "Supabase Storage is not configured "
            "(set SUPABASE_URL and SUPABASE_SERVICE_KEY)."
        )
    return (
        settings.supabase_url.rstrip("/"),
        settings.supabase_service_key,
        settings.supabase_storage_bucket,
    )


async def upload_image(data: bytes, mime_type: str) -> str:
    """Upload image bytes to Supabase Storage; return the public URL."""
    base, key, bucket = _config()
    path = f"{uuid.uuid4()}.{_MIME_EXT.get(mime_type, 'bin')}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{base}/storage/v1/object/{bucket}/{path}",
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": mime_type,
                "x-upsert": "true",
            },
            content=data,
        )
        resp.raise_for_status()
    return f"{base}/storage/v1/object/public/{bucket}/{path}"


async def delete_image(public_url: str) -> None:
    """Delete an object previously uploaded via upload_image (best-effort)."""
    base, key, bucket = _config()
    marker = f"/storage/v1/object/public/{bucket}/"
    if marker not in public_url:
        return
    path = public_url.split(marker, 1)[1]
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.delete(
            f"{base}/storage/v1/object/{bucket}/{path}",
            headers={"Authorization": f"Bearer {key}", "apikey": key},
        )
        if resp.status_code not in (200, 404):
            resp.raise_for_status()
