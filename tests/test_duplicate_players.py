"""Protezione contro schede duplicate e filtro delle rose pubbliche."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, schemas
from app.database import Base
from app.routers.registrations import approve_and_invite
from app.routers.teams import list_teams, get_team


def make_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def test_public_roster_excludes_inactive_players():
    engine, db = make_session()
    try:
        team = models.Team(name="Prima Divisione", category="Prima Divisione Femminile", season="2026/2027")
        db.add(team)
        db.flush()
        db.add_all([
            models.Player(team_id=team.id, first_name="Attiva", last_name="Atleta", is_active=True),
            models.Player(team_id=team.id, first_name="Ex", last_name="Atleta", is_active=False),
        ])
        db.commit()
        db.expire_all()
        result = list_teams(active_only=True, db=db)
        assert len(result) == 1
        assert [p.first_name for p in result[0].players] == ["Attiva"]
        db.expire_all()
        detail = get_team(team.id, db=db)
        assert [p.first_name for p in detail.players] == ["Attiva"]
    finally:
        db.close()
        engine.dispose()


def test_repeated_registration_approval_is_rejected_before_creating_new_player():
    engine, db = make_session()
    try:
        team = models.Team(name="Prima Divisione", category="Prima Divisione Femminile", season="2026/2027")
        db.add(team)
        db.flush()
        player = models.Player(team_id=team.id, first_name="Anna", last_name="Rossi", birth_date=date(2005, 1, 2))
        db.add(player)
        db.flush()
        registration = models.Registration(
            first_name="Anna", last_name="Rossi", birth_date=date(2005, 1, 2),
            email="example@example.invalid", phone="1234567890", player_id=player.id,
            status=models.RegistrationStatus.approved,
        )
        db.add(registration)
        db.commit()
        payload = schemas.RegistrationApprove(
            team_id=team.id, guardian_first_name="Genitore",
            guardian_last_name="Rossi", guardian_email="parent@example.invalid",
        )
        try:
            approve_and_invite(registration.id, payload, db=db, _=None)
            assert False, "Expected HTTP 409"
        except HTTPException as error:
            assert error.status_code == 409
        assert db.query(models.Player).count() == 1
    finally:
        db.close()
        engine.dispose()
