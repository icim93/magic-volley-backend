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
- GalleryPhoto: foto della fotogallery pubblica, organizzate per categoria
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
    superadmin = "superadmin"
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


class RevisionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


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
    height_cm = Column(Integer, nullable=True)
    bio = Column(Text, nullable=True)  # breve presentazione mostrata nella scheda pubblica
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

    # Preferenze di categoria per le notifiche push, scelte dal genitore stesso
    # (a livello di account, non di singolo dispositivo). Un messaggio diretto
    # inviato dallo staff (es. "assente oggi") non passa da questi filtri.
    notify_news = Column(Boolean, default=True)
    notify_match_results = Column(Boolean, default=True)
    notify_match_reminders = Column(Boolean, default=True)

    players = relationship("Player", secondary=guardian_player_association, back_populates="guardians")
    push_subscriptions = relationship("PushSubscription", back_populates="guardian", cascade="all, delete-orphan")
    notifications = relationship(
        "Notification", back_populates="guardian", cascade="all, delete-orphan",
        order_by="desc(Notification.created_at)",
    )


class PushSubscription(Base):
    """
    Iscrizione alle notifiche push di un dispositivo di un genitore/atleta.
    Un genitore può averne più di una (telefono + computer). "endpoint" è
    l'URL del servizio push del browser (FCM, Mozilla...) ed è univoco per
    dispositivo/browser: se il push service risponde 404/410 vuol dire che
    l'utente ha disinstallato o revocato il permesso, e va cancellata.
    """
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    guardian_id = Column(Integer, ForeignKey("guardians.id"), nullable=False, index=True)
    endpoint = Column(String(1000), unique=True, nullable=False)
    p256dh_key = Column(String(255), nullable=False)
    auth_key = Column(String(255), nullable=False)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    guardian = relationship("Guardian", back_populates="push_subscriptions")


class Notification(Base):
    """
    Cronologia delle notifiche mandate a un genitore: una notifica push del
    sistema operativo sparisce non appena viene vista o toccata, quindi qui
    ne teniamo traccia per il "report notifiche" nell'area riservata — a
    prescindere da come sia stata recapitata (push o email di riserva).
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    guardian_id = Column(Integer, ForeignKey("guardians.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    read_at = Column(DateTime, nullable=True)

    guardian = relationship("Guardian", back_populates="notifications")


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)  # es. "Allenatore", "Vice", "Dirigente"
    area = Column(String(50), nullable=False, default="collaboratori")  # dirigenza | staff_tecnico | area_sanitaria | collaboratori — assegnata a mano dall'admin, non più indovinata dal ruolo
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
    reminder_sent = Column(Boolean, default=False)  # promemoria push già inviato, evita doppi invii dal cron orario

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


class NewsRevision(Base):
    """
    Proposta di un articolo nuovo o di modifica a uno esistente, in attesa di
    approvazione da admin/superadmin. Contiene lo stato COMPLETO proposto
    (non un diff): all'approvazione i campi vengono applicati così come sono.
    La riga News collegata (se news_id è valorizzato) non viene mai toccata
    finché la proposta non è approvata, così un articolo già pubblicato resta
    visibile e invariato mentre una modifica è in coda.
    """
    __tablename__ = "news_revisions"

    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, ForeignKey("news.id"), nullable=True)  # null = proposta di articolo nuovo
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    summary = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    cover_image_url = Column(String(500), nullable=True)
    published = Column(Boolean, default=False)
    submitted_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(RevisionStatus), default=RevisionStatus.pending, nullable=False)
    reject_reason = Column(Text, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    news = relationship("News")
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])


class Registration(Base):
    """Richiesta di iscrizione/tesseramento inviata dal sito pubblico."""
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=False)
    birth_place = Column(String(255), nullable=True)
    address = Column(String(500), nullable=True)
    city = Column(String(120), nullable=True)
    postal_code = Column(String(10), nullable=True)
    fiscal_code = Column(String(20), nullable=True)
    parent_name = Column(String(255), nullable=True)  # se minorenne
    parent_birth_place = Column(String(255), nullable=True)  # se minorenne
    parent_address = Column(String(500), nullable=True)  # se minorenne
    parent_city = Column(String(120), nullable=True)  # se minorenne
    parent_postal_code = Column(String(10), nullable=True)  # se minorenne
    parent_fiscal_code = Column(String(20), nullable=True)  # se minorenne
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
    documents_accepted_at = Column(DateTime, nullable=True)  # step 2 del form: Regolamento/Statuto/Privacy/Foto/Safe Guarding


class GalleryPhoto(Base):
    """Foto della fotogallery pubblica (partite, allenamenti, eventi...)."""
    __tablename__ = "gallery_photos"

    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String(500), nullable=False)
    caption = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)  # es. "Partite", "Allenamenti", "Eventi"
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Sponsor(Base):
    __tablename__ = "sponsors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    logo_url = Column(String(500), nullable=False)
    website_url = Column(String(500), nullable=True)
    tier = Column(String(50), default="standard")  # es. "main", "gold", "standard"
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class Document(Base):
    """Documenti condivisi nel pannello (scout gara, materiale allenatori, ecc.),
    non pubblici: visibili solo a chi accede al pannello gestionale."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)  # etichetta libera, es. "Scouting", "Materiale allenatori"
    file_url = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=True)  # nome file originale, mostrato nella lista
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    uploaded_by = relationship("User")
