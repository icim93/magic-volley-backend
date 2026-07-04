"""
Modelli dati per Magic Volley Adelfia.

Entità principali:
- User: account admin/staff per il pannello gestionale
- Team: le squadre della società (es. 2ª Divisione, U16, U18)
- Player: giocatrici, collegate a una squadra
- Staff: allenatori/dirigenti, collegati a una o piu' squadre
- Match: partite (calendario + risultati)
- News: articoli del blog/news
- Registration: richieste di iscrizione/tesseramento
- Sponsor: sponsor e partner con logo e link
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, Float,
    ForeignKey, Enum, Table
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"


class RegistrationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    payment_due = "payment_due"
    completed = "completed"


class MatchStatus(str, enum.Enum):
    scheduled = "scheduled"
    played = "played"
    postponed = "postponed"
    cancelled = "cancelled"


# Tabella molti-a-molti Staff <-> Team (un allenatore può seguire più squadre)
staff_team_association = Table(
    "staff_team",
    Base.metadata,
    Column("staff_id", Integer, ForeignKey("staff.id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("teams.id"), primary_key=True),
)


class User(Base):
    """Account per il pannello gestionale (non le giocatrici)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.staff, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # es. "Serie 2ª Divisione"
    category = Column(String(100), nullable=False)  # es. "U16", "U18", "Senior"
    season = Column(String(20), nullable=False)  # es. "2025/2026"
    description = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    players = relationship("Player", back_populates="team", cascade="all, delete-orphan")
    staff = relationship("Staff", secondary=staff_team_association, back_populates="teams")
    home_matches = relationship(
        "Match", foreign_keys="Match.home_team_id", back_populates="home_team"
    )


# Tabella molti-a-molti Guardian <-> Player (un genitore può avere più figli in società,
# e in teoria una giocatrice può avere più di un genitore con accesso, es. madre e padre)
guardian_player_association = Table(
    "guardian_player",
    Base.metadata,
    Column("guardian_id", Integer, ForeignKey("guardians.id"), primary_key=True),
    Column("player_id", Integer, ForeignKey("players.id"), primary_key=True),
)


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    jersey_number = Column(Integer, nullable=True)
    role = Column(String(50), nullable=True)  # es. "schiacciatrice", "palleggiatrice", "libero"
    birth_date = Column(Date, nullable=True)
    photo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    team = relationship("Team", back_populates="players")
    guardians = relationship("Guardian", secondary=guardian_player_association, back_populates="players")


class Guardian(Base):
    """
    Account di un genitore/tutore per l'area riservata del sito.
    Creato SOLO dallo staff quando approva un'iscrizione (nessuna auto-registrazione pubblica).
    L'account resta inattivo (is_active=False, senza password) finché il genitore non clicca
    il link di attivazione ricevuto via email e imposta la propria password.
    """
    __tablename__ = "guardians"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # null finché non attiva l'account
    is_active = Column(Boolean, default=False)
    activation_token = Column(String(255), unique=True, nullable=True, index=True)
    activation_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    players = relationship("Player", secondary=guardian_player_association, back_populates="guardians")



class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)  # es. "Allenatore", "Vice", "Dirigente"
    bio = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    teams = relationship("Team", secondary=staff_team_association, back_populates="staff")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_team_name = Column(String(255), nullable=False)  # ridondante ma comodo per squadre "nostre" vs avversarie
    away_team_name = Column(String(255), nullable=False)
    is_home = Column(Boolean, default=True)  # partita in casa o fuori
    match_date = Column(DateTime, nullable=False)
    location = Column(String(255), nullable=True)  # palestra/indirizzo
    status = Column(Enum(MatchStatus), default=MatchStatus.scheduled)
    home_sets = Column(Integer, nullable=True)
    away_sets = Column(Integer, nullable=True)
    set_scores = Column(String(100), nullable=True)  # es. "25-20, 22-25, 25-18"
    notes = Column(Text, nullable=True)

    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    summary = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    cover_image_url = Column(String(500), nullable=True)
    published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    author = relationship("User")


class Registration(Base):
    """Richiesta di iscrizione/tesseramento inviata dal sito pubblico."""
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=False)
    parent_name = Column(String(255), nullable=True)  # se minorenne
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    requested_team_category = Column(String(100), nullable=True)  # es. "U16"
    medical_certificate_url = Column(String(500), nullable=True)
    id_document_url = Column(String(500), nullable=True)
    status = Column(Enum(RegistrationStatus), default=RegistrationStatus.pending)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    guardian_id = Column(Integer, ForeignKey("guardians.id"), nullable=True)


class Sponsor(Base):
    __tablename__ = "sponsors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    logo_url = Column(String(500), nullable=False)
    website_url = Column(String(500), nullable=True)
    tier = Column(String(50), default="standard")  # es. "main", "gold", "standard"
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
