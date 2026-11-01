"""Test di sicurezza della rimozione della partita dimostrativa."""
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base
from app.cleanup_test_match import remove_test_vs_test_match


def test_remove_only_september_demo_and_keep_official_matches():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        team = models.Team(name="Prima Divisione Femminile", category="Prima Divisione Femminile", season="2026/2027")
        db.add(team)
        db.flush()
        demo = models.Match(
            home_team_id=team.id, home_team_name="test", away_team_name="test",
            match_date=datetime(2026, 9, 1, 10, 0), home_sets=3, away_sets=0,
            status=models.MatchStatus.played,
        )
        official = models.Match(
            home_team_id=team.id, home_team_name="MAGIC VOLLEY ADELFIA A.S.D.",
            away_team_name="EUREKA GAS&POWER RAINBOW SPORT",
            match_date=datetime(2026, 10, 31, 18, 0), home_sets=1,
            away_sets=3, status=models.MatchStatus.played,
        )
        other_test = models.Match(
            home_team_id=team.id, home_team_name="test", away_team_name="test",
            match_date=datetime(2026, 9, 2, 10, 0), home_sets=3,
            away_sets=0, status=models.MatchStatus.played,
        )
        db.add_all([demo, official, other_test])
        db.commit()
        assert remove_test_vs_test_match(db) is True
        assert db.query(models.Match).count() == 2
        assert db.query(models.Match).filter(models.Match.id == official.id).count() == 1
        assert db.query(models.Match).filter(models.Match.id == other_test.id).count() == 1
        assert remove_test_vs_test_match(db) is False
    finally:
        db.close()
        engine.dispose()


def test_ambiguous_demo_matches_are_not_deleted():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        team = models.Team(name="Prima Divisione Femminile", category="Prima Divisione Femminile", season="2026/2027")
        db.add(team)
        db.flush()
        for hour in (10, 11):
            db.add(models.Match(
                home_team_id=team.id, home_team_name="test", away_team_name="test",
                match_date=datetime(2026, 9, 1, hour), home_sets=3, away_sets=0,
                status=models.MatchStatus.played,
            ))
        db.commit()
        assert remove_test_vs_test_match(db) is False
        assert db.query(models.Match).count() == 2
    finally:
        db.close()
        engine.dispose()
