"""Import idempotente della Prima Divisione Femminile 2026/2027.

I 18 incontri vengono aggiunti al database all'avvio del backend. Le gare gia'
presenti e gli eventuali risultati/cambi d'orario inseriti dal pannello admin
non sono sovrascritti.
"""
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)

SEASON = "2026/2027"
TEAM_NAME = "MAGIC VOLLEY ADELFIA A.S.D."
TEAM_CATEGORY = "Prima Divisione Femminile"
DATA_PATH = Path(__file__).parent / "data" / "calendario_2026_2027.json"
LOCK_KEY = 2026270181


def _normalize(value: str) -> str:
    """Confronto insensibile a maiuscole, punti e spazi nei nomi squadra."""
    return re.sub(r"[^a-z0-9]", "", (value or "").casefold())


def _resolve_team(db: Session) -> models.Team:
    """Collega le gare solo alla Prima Divisione Femminile della stagione."""
    teams = db.query(models.Team).filter(models.Team.season == SEASON).all()

    def is_first_division(team: models.Team) -> bool:
        category = _normalize(team.category)
        name = _normalize(team.name)
        first = ("primadivisione", "1adivisione", "1divisione")
        return any(value in category or value in name for value in first) and (
            "maschile" not in category and "maschile" not in name
        )

    matches = [team for team in teams if is_first_division(team)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError("Piu' squadre Prima Divisione Femminile 2026/2027: import sospeso")

    team = models.Team(
        name="Magic Volley Adelfia - Prima Divisione Femminile",
        category=TEAM_CATEGORY,
        season=SEASON,
        description="Campionato Prima Divisione Femminile 2026/2027",
        is_active=True,
    )
    db.add(team)
    db.flush()
    return team

def seed_magic_volley_2026_27(db: Session) -> dict:
    """Importa le gare mancanti. Rilanciare la funzione non crea duplicati."""
    fixtures = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if len(fixtures) != 18 or len({f["match_number"] for f in fixtures}) != 18:
        raise ValueError("Il calendario ufficiale deve contenere 18 gare distinte")

    # Su PostgreSQL evita import concorrenti da worker avviati in parallelo.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": LOCK_KEY})

    try:
        team = _resolve_team(db)
        existing = db.query(models.Match).filter(models.Match.home_team_id == team.id).all()
        known_ids = set()
        known_pairs = set()

        for match in existing:
            for found in re.findall(r"Gara FIPAV n\.\s*(\d+)", match.notes or "", flags=re.I):
                known_ids.add(int(found))
            known_pairs.add((
                _normalize(match.home_team_name),
                _normalize(match.away_team_name),
                bool(match.is_home),
            ))

        created = 0
        for fixture in fixtures:
            pair = (
                _normalize(fixture["home_team_name"]),
                _normalize(fixture["away_team_name"]),
                fixture["is_home"],
            )
            if fixture["match_number"] in known_ids or pair in known_pairs:
                continue

            db.add(models.Match(
                home_team_id=team.id,
                home_team_name=fixture["home_team_name"],
                away_team_name=fixture["away_team_name"],
                is_home=fixture["is_home"],
                # Orari civili italiani da calendario FIPAV. Il campo legacy
                # match_date e' un DateTime naive, come nelle altre gare.
                match_date=datetime.fromisoformat(fixture["match_date"]),
                location=fixture["location"],
                status=models.MatchStatus.scheduled,
                notes=f"Prima Divisione Femminile {SEASON} · Giornata {fixture['round']} · Gara FIPAV n. {fixture['match_number']}",
            ))
            known_ids.add(fixture["match_number"])
            known_pairs.add(pair)
            created += 1

        db.commit()
        logger.info("Calendario %s: %s nuove gare, %s gia' presenti", SEASON, created, len(fixtures) - created)
        return {"created": created, "existing": len(fixtures) - created, "team_id": team.id}
    except Exception:
        db.rollback()
        raise
