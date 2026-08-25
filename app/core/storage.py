"""
Upload immagini su Supabase Storage.

Usa httpx per parlare direttamente con le API REST di Supabase Storage
(niente SDK aggiuntivo). Richiede SUPABASE_URL e SUPABASE_SERVICE_KEY tra
le variabili d'ambiente; senza queste, upload_image solleva UploadError
e il chiamante lo trasforma in un 400 con un messaggio comprensibile.
"""
import os
import uuid

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "media")

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class UploadError(Exception):
    pass


def upload_image(content: bytes, content_type: str, folder: str = "uploads") -> str:
    """Carica un'immagine su Supabase Storage e ritorna il suo URL pubblico."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise UploadError("Caricamento immagini non configurato sul server (SUPABASE_URL/SUPABASE_SERVICE_KEY mancanti).")

    ext = ALLOWED_CONTENT_TYPES.get(content_type)
    if not ext:
        raise UploadError("Formato immagine non supportato: usa JPEG, PNG, WEBP o GIF.")

    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadError("Immagine troppo grande: massimo 5MB.")

    safe_folder = "".join(c for c in folder if c.isalnum() or c in ("-", "_")) or "uploads"
    path = f"{safe_folder}/{uuid.uuid4().hex}.{ext}"

    resp = httpx.post(
        f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{path}",
        content=content,
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "apikey": SUPABASE_SERVICE_KEY,
            "Content-Type": content_type,
        },
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise UploadError(f"Upload su Supabase Storage fallito ({resp.status_code}).")

    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{path}"
