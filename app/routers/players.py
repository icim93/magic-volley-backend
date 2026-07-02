from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.deps import require_admin

router = APIRouter(prefix="/api/players", tags=["Giocatrici"])


@router.get("", response_model=List[schemas.PlayerOut])
def list_players(team_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Player).filter(models.Player.is_active == True)  # noqa: E712
    if team_id is not None:
        query = query.filter(models.Player.team_id == team_id)
    return query.all()


@router.post("", response_model=schemas.PlayerOut, status_code=201)
def create_player(
    player_in: schemas.PlayerCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    team = db.query(models.Team).filter(models.Team.id == player_in.team_id).first()
    if not team:
        raise HTTPException(status_code=400, detail="Squadra indicata non esistente")
    player = models.Player(**player_in.model_dump())
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@router.patch("/{player_id}", response_model=schemas.PlayerOut)
def update_player(
    player_id: int,
    player_in: schemas.PlayerUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Giocatrice non trovata")
    for field, value in player_in.model_dump(exclude_unset=True).items():
        setattr(player, field, value)
    db.commit()
    db.refresh(player)
    return player


@router.delete("/{player_id}", status_code=204)
def delete_player(
    player_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Giocatrice non trovata")
    db.delete(player)
    db.commit()
