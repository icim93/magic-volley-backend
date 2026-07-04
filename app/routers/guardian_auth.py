from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.deps import get_current_guardian

router = APIRouter(prefix="/api/guardian-auth", tags=["Area riservata genitori"])


@router.post("/activate")
def activate_account(data: schemas.GuardianActivate, db: Session = Depends(get_db)):
    """
    Il genitore arriva qui dal link ricevuto via email dopo l'approvazione
    dell'iscrizione. Imposta la password e attiva l'account per la prima volta.
    """
    guardian = db.query(models.Guardian).filter(models.Guardian.activation_token == data.token).first()
    if not guardian:
        raise HTTPException(status_code=400, detail="Link di attivazione non valido.")
    if guardian.activation_token_expires and guardian.activation_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Il link di attivazione è scaduto. Contatta la società.")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="La password deve avere almeno 8 caratteri.")

    guardian.hashed_password = get_password_hash(data.password)
    guardian.is_active = True
    guardian.activation_token = None
    guardian.activation_token_expires = None
    db.commit()
    return {"message": "Account attivato correttamente. Ora puoi accedere."}


@router.post("/login", response_model=schemas.GuardianLoginOut)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    guardian = db.query(models.Guardian).filter(models.Guardian.email == form_data.username).first()
    if not guardian or not guardian.hashed_password or not verify_password(form_data.password, guardian.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o password non corretti.")
    if not guardian.is_active:
        raise HTTPException(status_code=403, detail="Account non ancora attivato. Controlla la tua email.")

    token = create_access_token(data={"sub": str(guardian.id), "type": "guardian"})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.GuardianMeOut)
def read_current_guardian(
    guardian: models.Guardian = Depends(get_current_guardian),
    db: Session = Depends(get_db),
):
    # Ricarica con le relazioni necessarie (players + team di ciascuna) già pronte.
    guardian = (
        db.query(models.Guardian)
        .options(joinedload(models.Guardian.players).joinedload(models.Player.team))
        .filter(models.Guardian.id == guardian.id)
        .first()
    )
    return guardian


@router.get("/matches", response_model=List[schemas.MatchOut])
def matches_for_my_children(
    guardian: models.Guardian = Depends(get_current_guardian),
    db: Session = Depends(get_db),
):
    """Calendario e risultati delle sole squadre in cui giocano i figli di questo genitore."""
    guardian = (
        db.query(models.Guardian)
        .options(joinedload(models.Guardian.players))
        .filter(models.Guardian.id == guardian.id)
        .first()
    )
    team_ids = {p.team_id for p in guardian.players}
    if not team_ids:
        return []
    return (
        db.query(models.Match)
        .filter(models.Match.home_team_id.in_(team_ids))
        .order_by(models.Match.match_date.desc())
        .all()
    )
