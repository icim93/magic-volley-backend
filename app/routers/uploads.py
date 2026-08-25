from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app import models
from app.core.deps import require_admin
from app.core.storage import UploadError, upload_image

router = APIRouter(prefix="/api/uploads", tags=["Upload"])


@router.post("")
async def create_upload(
    file: UploadFile = File(...),
    folder: str = Query("uploads"),
    _: models.User = Depends(require_admin),
):
    """Carica un'immagine (giocatrici, staff, news, sponsor, gallery, squadre)
    e ritorna l'URL pubblico da salvare nel campo *_url dell'entità."""
    content = await file.read()
    try:
        url = upload_image(content, file.content_type, folder)
    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"url": url}
