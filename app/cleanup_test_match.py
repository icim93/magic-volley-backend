"""Rimozione mirata della vecchia partita dimostrativa dal calendario pubblico.

Questa pulizia e' idempotente: elimina esclusivamente la gara fittizia
"test" vs "test" del 1 settembre 2026, con risultato 3-0.
Non modifica il calendario ufficiale o altre partite.
"""
import logging
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)


def remove_test_vs_test_match(db: Session) -> bool:
    matches = (
        db.query(models.Match)
        .filter(
            func.lower(func.trim(models.Match.home_team_name)) == "test",
            func.lower(func.trim(models.Match.away_team_name)) == "test",
            models.Match.match_date >= datetime(2026, 9, 1),
            models.Match.match_date < datetime(2026, 9, 2),
            models.Match.home_sets == 3,
            models.Match.away_sets == 0,
        )
        .all()
    )
    if not matches:
        return False

    if len(matches) > 1:
        logger.warning(
            "Rilevate %s gare test vs test del 01/09/2026: "
            "cancellazione sospesa per evitare ambiguita'",
            len(matches),
        )
        return False

    match = matches[0]
    match_id = match.id
    db.delete(match)
    db.commit()
    logger.info("Rimossa la partita dimostrativa test vs test, id=%s", match_id)
    return True
