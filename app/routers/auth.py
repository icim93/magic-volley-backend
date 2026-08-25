import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.deps import require_admin, require_superadmin, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Autenticazione"])


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login con email (come username) e password. Ritorna un JWT."""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password non corretti",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disattivato")

    token = create_access_token(data={"sub": str(user.id), "role": user.role.value, "type": "staff"})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(require_admin),
):
    """Crea un nuovo utente staff/admin per il pannello. Solo un admin può farlo,
    ma solo un superadmin può creare altri account admin/superadmin."""
    if user_in.role in (models.UserRole.admin, models.UserRole.superadmin) and current_admin.role != models.UserRole.superadmin:
        raise HTTPException(
            status_code=403,
            detail="Solo un superadmin può creare account admin",
        )

    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email già registrata")

    user = models.User(
        email=user_in.email,
        full_name=user_in.full_name,
        role=user_in.role,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class BootstrapSuperadminIn(BaseModel):
    email: str
    token: str


@router.post("/bootstrap-superadmin", include_in_schema=False)
def bootstrap_superadmin(data: BootstrapSuperadminIn, db: Session = Depends(get_db)):
    """Promuove UN utente esistente a superadmin, protetto da BOOTSTRAP_TOKEN
    (env var su Render). Pensato per il bootstrap iniziale su piani senza Shell:
    imposta BOOTSTRAP_TOKEN, chiama questo endpoint una volta, poi rimuovi la env var.
    Senza BOOTSTRAP_TOKEN impostata, l'endpoint è sempre disattivato."""
    expected_token = os.getenv("BOOTSTRAP_TOKEN")
    if not expected_token or not hmac.compare_digest(data.token, expected_token):
        raise HTTPException(status_code=404)

    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    user.role = models.UserRole.superadmin
    db.commit()
    return {"message": f"{data.email} è ora superadmin."}


@router.get("/users", response_model=List[schemas.UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(require_admin),
):
    """Elenco utenti staff/admin del pannello, per la sezione Utenti (solo admin+)."""
    return db.query(models.User).order_by(models.User.full_name).all()


@router.patch("/users/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(require_admin),
):
    """Modifica un utente esistente. Solo un superadmin può toccare account
    admin/superadmin (creare, promuovere o modificare); un admin normale può
    gestire solo gli account staff."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    involves_privileged_role = user.role in (models.UserRole.admin, models.UserRole.superadmin) or (
        user_in.role is not None and user_in.role in (models.UserRole.admin, models.UserRole.superadmin)
    )
    if involves_privileged_role and current_admin.role != models.UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Solo un superadmin può modificare account admin")

    if user.id == current_admin.id and (
        user_in.is_active is False or (user_in.role is not None and user_in.role != current_admin.role)
    ):
        raise HTTPException(status_code=400, detail="Non puoi disattivare o cambiare il tuo stesso ruolo da qui")

    if user_in.email is not None and user_in.email != user.email:
        existing = db.query(models.User).filter(models.User.email == user_in.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email già registrata")
        user.email = user_in.email

    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.role is not None:
        user.role = user_in.role
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)

    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(
    data: schemas.UserChangePassword,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cambio password su richiesta dell'utente stesso (admin o staff), dalla sezione profilo."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="La password attuale non è corretta.")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="La nuova password deve avere almeno 8 caratteri.")

    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password aggiornata correttamente."}
