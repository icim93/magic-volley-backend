from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/registrations", tags=["Iscrizioni"])


@router.post("", response_model=schemas.RegistrationOut, status_code=201)
def submit_registration(reg_in: schemas.RegistrationCreate, db: Session = Depends(get_db)):
    """
    Endpoint PUBBLICO: chiunque dal sito può inviare una richiesta di iscrizione.
    Nessuna autenticazione richiesta qui - è il form pubblico di tesseramento.
    """
    registration = models.Registration(**reg_in.model_dump())
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
