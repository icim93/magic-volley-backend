from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.deps import require_admin

router = APIRouter(prefix="/api/staff", tags=["Staff tecnico"])


def _resolve_teams(db: Session, team_ids: List[int]) -> List[models.Team]:
    if not team_ids:
        return []
    teams = db.query(models.Team).filter(models.Team.id.in_(team_ids)).all()
    if len(teams) != len(set(team_ids)):
        raise HTTPException(status_code=400, detail="Una o più squadre indicate non esistono")
    return teams


@router.get("", response_model=List[schemas.StaffOut])
def list_staff(db: Session = Depends(get_db)):
    return db.query(models.Staff).all()


@router.post("", response_model=schemas.StaffOut, status_code=201)
def create_staff(
    staff_in: schemas.StaffCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    data = staff_in.model_dump(exclude={"team_ids"})
    member = models.Staff(**data)
    member.teams = _resolve_teams(db, staff_in.team_ids)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.patch("/{staff_id}", response_model=schemas.StaffOut)
def update_staff(
    staff_id: int,
    staff_in: schemas.StaffUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    member = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Membro dello staff non trovato")
    data = staff_in.model_dump(exclude_unset=True, exclude={"team_ids"})
    for field, value in data.items():
        setattr(member, field, value)
    if staff_in.team_ids is not None:
        member.teams = _resolve_teams(db, staff_in.team_ids)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{staff_id}", status_code=204)
def delete_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    member = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Membro dello staff non trovato")
    db.delete(member)
    db.commit()
