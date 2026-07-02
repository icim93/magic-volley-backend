from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.deps import require_admin

router = APIRouter(prefix="/api/matches", tags=["Partite"])


@router.get("", response_model=List[schemas.MatchOut])
def list_matches(
    team_id: Optional[int] = None,
    upcoming_only: bool = False,
    db: Session = Depends(get_db),
):
    """Elenco partite, ordinate per data. upcoming_only=true per il calendario futuro."""
    query = db.query(models.Match)
    if team_id is not None:
        query = query.filter(models.Match.home_team_id == team_id)
    if upcoming_only:
        query = query.filter(models.Match.match_date >= datetime.utcnow())
    return query.order_by(models.Match.match_date.asc()).all()


@router.get("/results", response_model=List[schemas.MatchOut])
def list_results(team_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Solo partite già giocate, più recenti prima."""
    query = db.query(models.Match).filter(models.Match.status == models.MatchStatus.played)
    if team_id is not None:
        query = query.filter(models.Match.home_team_id == team_id)
    return query.order_by(models.Match.match_date.desc()).all()


@router.post("", response_model=schemas.MatchOut, status_code=201)
def create_match(
    match_in: schemas.MatchCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    team = db.query(models.Team).filter(models.Team.id == match_in.home_team_id).first()
    if not team:
        raise HTTPException(status_code=400, detail="Squadra indicata non esistente")
    match = models.Match(**match_in.model_dump())
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.patch("/{match_id}", response_model=schemas.MatchOut)
def update_match(
    match_id: int,
    match_in: schemas.MatchUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """Usato anche per inserire il risultato dopo la partita (sets, punteggi, status=played)."""
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Partita non trovata")
    for field, value in match_in.model_dump(exclude_unset=True).items():
        setattr(match, field, value)
    db.commit()
    db.refresh(match)
    return match


@router.delete("/{match_id}", status_code=204)
def delete_match(
    match_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Partita non trovata")
    db.delete(match)
    db.commit()
