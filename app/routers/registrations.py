from typing import List, Optional
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.deps import get_current_user, require_superadmin
from app.core.security import get_password_hash
from app.core.email import send_activation_email
import os

router = APIRouter(prefix="/api/registrations", tags=["Iscrizioni"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@router.post("", response_model=schemas.RegistrationOut, status_code=201)
def submit_registration(reg_in: schemas.RegistrationCreate, db: Session = Depends(get_db)):
    """
    Endpoint PUBBLICO: chiunque dal sito può inviare una richiesta di iscrizione.
    Nessuna autenticazione richiesta qui - è il form pubblico di tesseramento.
    """
    data = reg_in.model_dump(exclude={"documents_accepted"})
    registration = models.Registration(**data)
    if reg_in.documents_accepted:
        registration.documents_accepted_at = datetime.utcnow()
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


@router.get("", response_model=List[schemas.RegistrationOut])
def list_registrations(
    status: Optional[models.RegistrationStatus] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),  # protetto: solo staff/admin vedono le iscrizioni
):
    query = db.query(models.Registration)
    if status is not None:
        query = query.filter(models.Registration.status == status)
    return query.order_by(models.Registration.created_at.desc()).all()


@router.patch("/{registration_id}", response_model=schemas.RegistrationOut)
def update_registration(
    registration_id: int,
    reg_in: schemas.RegistrationUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Usato dallo staff per approvare/rifiutare, aggiungere note, aggiornare stato pagamento."""
    registration = db.query(models.Registration).filter(
        models.Registration.id == registration_id
    ).first()
    if not registration:
        raise HTTPException(status_code=404, detail="Iscrizione non trovata")
    for field, value in reg_in.model_dump(exclude_unset=True).items():
        setattr(registration, field, value)
    db.commit()
    db.refresh(registration)
    return registration


@router.delete("/{registration_id}", status_code=204)
def delete_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_superadmin),
):
    """Elimina definitivamente una richiesta di iscrizione (es. richieste di prova).
    Solo superadmin: è un'operazione distruttiva e non recuperabile. Non tocca
    l'eventuale giocatrice/genitore già creati approvando la richiesta."""
    registration = db.query(models.Registration).filter(models.Registration.id == registration_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="Iscrizione non trovata")
    db.delete(registration)
    db.commit()


@router.post("/{registration_id}/approve-and-invite", response_model=schemas.RegistrationApproveOut)
def approve_and_invite(
    registration_id: int,
    data: schemas.RegistrationApprove,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """
    Approva una richiesta di iscrizione: crea la giocatrice nella squadra scelta,
    crea (o riusa) l'account del genitore, li collega, e invia l'email di attivazione.
    Questo è l'UNICO modo in cui viene creato un account genitore: nessuna
    auto-registrazione pubblica è prevista.
    """
    registration = db.query(models.Registration).filter(models.Registration.id == registration_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="Iscrizione non trovata")

    team = db.query(models.Team).filter(models.Team.id == data.team_id).first()
    if not team:
        raise HTTPException(status_code=400, detail="Squadra indicata non esistente")

    # Una richiesta gia' approvata non puo' generare nuove schede,
    # anche se il pulsante viene premuto due volte.
    if registration.player_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Questa iscrizione e' gia' collegata a una giocatrice: non e' stata creata una seconda scheda.",
        )

    # Se esiste gia' la stessa persona nella stessa squadra, non creare
    # un record parallelo: l'admin puo' verificare e collegare i dati correttamente.
    existing_player = (
        db.query(models.Player)
        .filter(
            models.Player.team_id == team.id,
            models.Player.birth_date == registration.birth_date,
            models.Player.first_name.ilike(registration.first_name.strip()),
            models.Player.last_name.ilike(registration.last_name.strip()),
        )
        .first()
    )
    if existing_player is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Giocatrice gia' presente in questa squadra (scheda ID "
                f"{existing_player.id}). Verificare e collegare l'iscrizione "
                "alla scheda esistente anziche' creare un duplicato."
            ),
        )

    # 1. Crea la giocatrice a partire dai dati della richiesta
    player = models.Player(
        team_id=team.id,
        first_name=registration.first_name,
        last_name=registration.last_name,
        birth_date=registration.birth_date,
        jersey_number=data.jersey_number,
    )
    db.add(player)
    db.flush()  # per avere player.id prima del commit finale

    # 2. Trova o crea il genitore
    guardian = db.query(models.Guardian).filter(models.Guardian.email == data.guardian_email).first()
    email_needed = True
    if guardian and guardian.is_active:
        # Genitore già attivo (es. fratello/sorella già iscritti): niente nuova email di attivazione.
        email_needed = False
    if not guardian:
        guardian = models.Guardian(
            first_name=data.guardian_first_name,
            last_name=data.guardian_last_name,
            email=data.guardian_email,
        )
        db.add(guardian)
        db.flush()

    activation_link = f"{FRONTEND_URL}/attiva-account"
    email_sent = False
    if email_needed:
        guardian.activation_token = secrets.token_urlsafe(32)
        guardian.activation_token_expires = datetime.utcnow() + timedelta(days=7)
        activation_link = f"{FRONTEND_URL}/attiva-account?token={guardian.activation_token}"

    # 3. Collega genitore e giocatrice (evita duplicati se già collegati)
    if player not in guardian.players:
        guardian.players.append(player)

    # 4. Aggiorna la richiesta di iscrizione
    registration.status = models.RegistrationStatus.approved
    registration.player_id = player.id
    registration.guardian_id = guardian.id

    db.commit()
    db.refresh(player)

    if email_needed:
        email_sent = send_activation_email(guardian.email, guardian.first_name, activation_link)

    return schemas.RegistrationApproveOut(
        player=player,
        guardian_email=guardian.email,
        email_sent=email_sent,
        activation_link=activation_link,
    )
