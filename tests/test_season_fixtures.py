"""Test dell'import calendario con SQLite isolato (nessun DB di produzione)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base
from app.season_fixtures import seed_magic_volley_2026_27


def test_import_18_matches_once_and_preserves_results():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        first = seed_magic_volley_2026_27(session)
        assert first["created"] == 18
        assert session.query(models.Match).count() == 18
        games = session.query(models.Match).all()
        assert sum(1 for match in games if match.is_home) == 9
        assert sum(1 for match in games if not match.is_home) == 9
        assert len({(m.home_team_name, m.away_team_name) for m in games}) == 18
        assert any("Gara FIPAV n. 270" in (m.notes or "") for m in games)

        first_match = next(m for m in games if "Gara FIPAV n. 181" in m.notes)
        first_match.status = models.MatchStatus.played
        first_match.home_sets = 3
        first_match.away_sets = 1
        session.commit()
        second = seed_magic_volley_2026_27(session)
        assert second["created"] == 0
        assert second["existing"] == 18
        assert session.query(models.Match).count() == 18
        session.refresh(first_match)
        assert first_match.status == models.MatchStatus.played
        assert (first_match.home_sets, first_match.away_sets) == (3, 1)
    finally:
        session.close()
        engine.dispose()
