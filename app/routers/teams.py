from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.core.deps import require_admin

router = APIRouter(prefix="/api/teams", tags=["Squadre"])


@router.get("", response_model=List[schemas.TeamWithPlayersOut])
def list_teams(active_only: bool = True, db: Session = Depends(get_db)):
    """Elenco squadre, pubblico. Include roster giocatrici."""
    query = db.query(models.Team).options(joinedload(models.Team.players))
    if active_only:
        query = query.filter(models.Team.is_active == True)  # noqa: E712
    return query.all()


@router.get("/{team_id}", response_model=schemas.TeamWithPlayersOut)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = (
        db.query(models.Team)
        .options(joinedload(models.Team.players))
        .filter(models.Team.id == team_id)
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Squadra non trovata")
    return team


@router.post("", response_model=schemas.TeamOut, status_code=201)
def create_team(
    team_in: schemas.TeamCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    team = models.Team(**team_in.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.patch("/{team_id}", response_model=schemas.TeamOut)
def update_team(
    team_id: int,
    team_in: schemas.TeamUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Squadra non trovata")
    for field, value in team_in.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=204)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Squadra non trovata")
    db.delete(team)
    db.commit()
