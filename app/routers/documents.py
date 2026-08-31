from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.core.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/documents", tags=["Documenti"])


@router.get("", response_model=List[schemas.DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Elenco documenti condivisi nel pannello. Visibile a staff/admin/superadmin."""
    return (
        db.query(models.Document)
        .options(joinedload(models.Document.uploaded_by))
        .order_by(models.Document.created_at.desc())
        .all()
    )


@router.post("", response_model=schemas.DocumentOut, status_code=201)
def create_document(
    doc_in: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Registra un documento già caricato su storage (vedi /api/uploads). Chiunque
    acceda al pannello può caricare."""
    document = models.Document(**doc_in.model_dump(), uploaded_by_id=current_user.id)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """Elimina un documento. Solo admin+ (lo staff può caricare ma non cancellare)."""
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    db.delete(document)
    db.commit()
