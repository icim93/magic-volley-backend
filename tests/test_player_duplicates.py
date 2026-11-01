"""Test fusione controllata schede atleta."""
from datetime import date
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base
from app.routers.player_duplicates import MergeRequest, list_duplicate_groups, merge_duplicate_players


def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def test_merge_complementary_data_and_links():
    engine, db = session()
    try:
        team = models.Team(name="Prima Divisione", category="Prima Divisione Femminile", season="2026/2027")
        db.add(team)
        db.flush()
        keep = models.Player(team_id=team.id, first_name="Anna", last_name="Rossi",
                             jersey_number=21, is_active=True)
        other = models.Player(team_id=team.id, first_name="ANNA", last_name="ROSSI",
                              birth_date=date(2004, 2, 3), photo_url="https://example.invalid/photo.jpg")
        db.add_all([keep, other])
        db.flush()
        guardian = models.Guardian(first_name="Paola", last_name="Rossi", email="parent@example.invalid")
        guardian.players.append(other)
        db.add(guardian)
        reg = models.Registration(first_name="Anna", last_name="Rossi", birth_date=date(2004, 2, 3),
                                  email="anna@example.invalid", phone="123456789", player_id=other.id)
        db.add(reg)
        db.commit()
        groups = list_duplicate_groups(db=db, _=None)
        assert len(groups) == 1
        assert groups[0]["conflicts"] == []
        response = merge_duplicate_players(MergeRequest(keep_id=keep.id, merge_id=other.id), db=db, _=None)
        assert response["archived_not_deleted"] is True
        assert response["registrations_moved"] == 1
        db.refresh(keep)
        db.refresh(other)
        db.refresh(reg)
        assert keep.jersey_number == 21
        assert keep.birth_date == date(2004, 2, 3)
        assert keep.photo_url == "https://example.invalid/photo.jpg"
        assert guardian in keep.guardians
        assert reg.player_id == keep.id
        assert other.merged_into_player_id == keep.id and other.is_active is False
        assert list_duplicate_groups(db=db, _=None) == []
    finally:
        db.close()
        engine.dispose()


def test_conflicting_date_blocks_merge_and_keeps_records():
    engine, db = session()
    try:
        team = models.Team(name="Prima Divisione", category="Prima Divisione Femminile", season="2026/2027")
        db.add(team)
        db.flush()
        a = models.Player(team_id=team.id, first_name="Anna", last_name="Rossi",
                          birth_date=date(2004, 2, 3))
        b = models.Player(team_id=team.id, first_name="Anna", last_name="Rossi",
                          birth_date=date(2003, 2, 3))
        db.add_all([a,b])
        db.commit()
        try:
            merge_duplicate_players(MergeRequest(keep_id=a.id,merge_id=b.id), db=db, _=None)
            assert False
        except HTTPException as exc:
            assert exc.status_code == 409
        assert db.query(models.Player).count() == 2
    finally:
        db.close()
        engine.dispose()


def test_same_name_different_team_is_not_a_duplicate_group():
    engine, db = session()
    try:
        t1 = models.Team(name="Prima", category="Prima Divisione Femminile", season="2026/2027")
        t2 = models.Team(name="Under 18", category="U18", season="2026/2027")
        db.add_all([t1,t2])
        db.flush()
        a = models.Player(team_id=t1.id, first_name="Anna", last_name="Rossi")
        b = models.Player(team_id=t2.id, first_name="Anna", last_name="Rossi")
        db.add_all([a,b])
        db.commit()
        assert list_duplicate_groups(db=db, _=None) == []
        try:
            merge_duplicate_players(MergeRequest(keep_id=a.id,merge_id=b.id), db=db, _=None)
            assert False
        except HTTPException as exc:
            assert exc.status_code == 409
    finally:
        db.close()
        engine.dispose()
