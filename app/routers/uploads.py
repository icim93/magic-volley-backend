from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app import models
from app.core.deps import get_current_user
from app.core.storage import UploadError, upload_file

router = APIRouter(prefix="/api/uploads", tags=["Upload"])


@router.post("")
async def create_upload(
    file: UploadFile = File(...),
    folder: str = Query("uploads"),
    _: models.User = Depends(get_current_user),
):
    """Carica un file (immagine o documento) e ritorna l'URL pubblico.
    Usato sia per i campi immagine delle entità pubbliche (giocatrici, staff,
    news, sponsor, gallery, squadre — la mutazione che salva l'URL resta
    admin-gated) sia per la sezione Documenti del pannello, accessibile anche
    allo staff."""
    content = await file.read()
    try:
        url = upload_file(content, file.content_type, folder)
    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"url": url}
