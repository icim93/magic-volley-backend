from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.deps import require_admin

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
    """Crea un nuovo utente staff/admin per il pannello. Solo un admin può farlo."""
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


@router.get("/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(require_admin)):
    return current_user
