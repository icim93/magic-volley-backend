"""Merge sicuro delle schede omonime nella stessa squadra e stagione.

Nessuna unione automatica all'avvio: l'amministratore deve controllare
l'anteprima e scegliere esplicitamente la scheda da conservare.
"""
import re
import unicodedata
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.core.deps import require_admin

router = APIRouter(prefix="/api/player-duplicates", tags=["Giocatrici duplicate"])

COMPLEMENTARY = ("birth_date", "jersey_number", "role", "height_cm", "bio", "photo_url")


def normalized(value):
    value = unicodedata.normalize("NFKD", (value or "").strip().casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", value)


def filled(value):
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def conflict_fields(a, b):
    return [
        name for name in COMPLEMENTARY
        if filled(getattr(a, name)) and filled(getattr(b, name))
        and getattr(a, name) != getattr(b, name)
    ]


def player_snapshot(p, db):
    return {
        "id": p.id,
        "team_id": p.team_id,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "is_active": p.is_active,
        "birth_date": p.birth_date.isoformat() if p.birth_date else None,
        "jersey_number": p.jersey_number,
        "role": p.role,
        "height_cm": p.height_cm,
        "bio": p.bio,
        "photo_url": p.photo_url,
        "registrations_count": db.query(models.Registration).filter(
            models.Registration.player_id == p.id
        ).count(),
        "guardians_count": len(p.guardians),
    }


@router.get("")
def list_duplicate_groups(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    teams = {team.id: team for team in db.query(models.Team).all()}
    grouped = defaultdict(list)
    for player in db.query(models.Player).filter(
        models.Player.merged_into_player_id.is_(None)
    ).order_by(models.Player.id).all():
        key = (player.team_id, normalized(player.first_name), normalized(player.last_name))
        grouped[key].append(player)

    groups = []
    for (team_id, first_name, last_name), players in grouped.items():
        if len(players) < 2:
            continue
        conflicts = sorted({
            field
            for i, p in enumerate(players)
            for other in players[i + 1:]
            for field in conflict_fields(p, other)
        })
        team = teams.get(team_id)
        groups.append({
            "team_id": team_id,
            "team_name": team.name if team else "",
            "category": team.category if team else "",
            "season": team.season if team else "",
            "name": f"{players[0].first_name} {players[0].last_name}",
            "conflicts": conflicts,
            "players": [player_snapshot(p, db) for p in players],
        })
    return groups


class MergeRequest(BaseModel):
    keep_id: int = Field(gt=0)
    merge_id: int = Field(gt=0)


@router.post("/merge")
def merge_duplicate_players(
    payload: MergeRequest,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    if payload.keep_id == payload.merge_id:
        raise HTTPException(400, "Seleziona due schede differenti")

    ids = sorted((payload.keep_id, payload.merge_id))
    players = db.query(models.Player).filter(models.Player.id.in_(ids)).order_by(
        models.Player.id
    ).with_for_update().all()
    if len(players) != 2:
        raise HTTPException(404, "Una delle schede non esiste")

    by_id = {p.id: p for p in players}
    keep, other = by_id[payload.keep_id], by_id[payload.merge_id]
    if keep.merged_into_player_id is not None or other.merged_into_player_id is not None:
        raise HTTPException(409, "Una delle schede e' gia' stata accorpata")
    if keep.team_id != other.team_id:
        raise HTTPException(409, "Non unire schede appartenenti a squadre diverse")
    if (
        normalized(keep.first_name) != normalized(other.first_name)
        or normalized(keep.last_name) != normalized(other.last_name)
    ):
        raise HTTPException(409, "Nome e cognome non coincidono")

    conflicts = conflict_fields(keep, other)
    if conflicts:
        raise HTTPException(
            status_code=409,
            detail="Dati discordanti (" + ", ".join(conflicts) + "): "
                   "controlla le schede e risolvi le differenze prima dell'unione",
        )

    try:
        copied = []
        for field in COMPLEMENTARY:
            a, b = getattr(keep, field), getattr(other, field)
            if not filled(a) and filled(b):
                setattr(keep, field, b)
                copied.append(field)

        keep.is_active = bool(keep.is_active or other.is_active)
        # Trasferisce genitori/tutori e iscrizioni che puntano alla scheda secondaria.
        for guardian in list(other.guardians):
            if guardian not in keep.guardians:
                keep.guardians.append(guardian)
            other.guardians.remove(guardian)
        registrations_moved = db.query(models.Registration).filter(
            models.Registration.player_id == other.id
        ).update({models.Registration.player_id: keep.id}, synchronize_session=False)

        other.is_active = False
        other.merged_into_player_id = keep.id
        db.commit()
        return {
            "kept_id": keep.id,
            "archived_id": other.id,
            "copied_fields": copied,
            "registrations_moved": registrations_moved,
            "archived_not_deleted": True,
        }
    except Exception:
        db.rollback()
        raise
