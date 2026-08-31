import os
import secrets
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.core.deps import require_admin
from app.core.email import send_activation_email

router = APIRouter(prefix="/api/guardians", tags=["Genitori"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@router.get("", response_model=List[schemas.GuardianAdminOut])
def list_guardians(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """Elenco genitori (area riservata famiglie), con le figlie/i collegati.
    Serve a vedere gli account creati approvando le iscrizioni, altrimenti
    invisibili nel pannello."""
    return (
        db.query(models.Guardian)
        .options(joinedload(models.Guardian.players).joinedload(models.Player.team))
        .order_by(models.Guardian.created_at.desc())
        .all()
    )


@router.post("/{guardian_id}/regenerate-activation-link", response_model=schemas.GuardianActivationLinkOut)
def regenerate_activation_link(
    guardian_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """Rigenera il link di attivazione per un genitore non ancora attivo — utile
    se il link mostrato al momento dell'approvazione è andato perso, o se
    l'email non è mai arrivata."""
    guardian = db.query(models.Guardian).filter(models.Guardian.id == guardian_id).first()
    if not guardian:
        raise HTTPException(status_code=404, detail="Genitore non trovato")
    if guardian.is_active:
        raise HTTPException(status_code=400, detail="Questo account è già attivo, non serve un nuovo link")

    guardian.activation_token = secrets.token_urlsafe(32)
    guardian.activation_token_expires = datetime.utcnow() + timedelta(days=7)
    db.commit()

    activation_link = f"{FRONTEND_URL}/attiva-account?token={guardian.activation_token}"
    email_sent = send_activation_email(guardian.email, guardian.first_name, activation_link)

    return schemas.GuardianActivationLinkOut(activation_link=activation_link, email_sent=email_sent)
