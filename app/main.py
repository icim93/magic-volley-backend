"""
Entry point dell'applicazione Magic Volley Adelfia - Backend API.

Avvio in locale:
    uvicorn app.main:app --reload

Documentazione interattiva disponibile su /docs (Swagger) una volta avviato.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.database import engine, Base
from app.routers import auth, teams, players, staff, matches, news, registrations, sponsors, guardian_auth, gallery, sitemap, uploads, documents

# Crea le tabelle nel DB se non esistono già.
# Per modifiche allo schema in futuro conviene passare ad Alembic (già incluso nei requirements).
Base.metadata.create_all(bind=engine)


def _ensure_new_columns():
    """create_all non aggiunge colonne a tabelle già esistenti: qui le aggiungiamo a mano."""
    inspector = inspect(engine)

    players_existing = {c["name"] for c in inspector.get_columns("players")}
    registrations_existing = {c["name"] for c in inspector.get_columns("registrations")}
    staff_existing = {c["name"] for c in inspector.get_columns("staff")}

    with engine.begin() as conn:
        if "height_cm" not in players_existing:
            conn.execute(text("ALTER TABLE players ADD COLUMN height_cm INTEGER"))
        if "bio" not in players_existing:
            conn.execute(text("ALTER TABLE players ADD COLUMN bio TEXT"))
        if "player_id" not in registrations_existing:
            conn.execute(text("ALTER TABLE registrations ADD COLUMN player_id INTEGER REFERENCES players(id)"))
        if "guardian_id" not in registrations_existing:
            conn.execute(text("ALTER TABLE registrations ADD COLUMN guardian_id INTEGER REFERENCES guardians(id)"))
        if "documents_accepted_at" not in registrations_existing:
            conn.execute(text("ALTER TABLE registrations ADD COLUMN documents_accepted_at TIMESTAMP"))
        if "area" not in staff_existing:
            conn.execute(text("ALTER TABLE staff ADD COLUMN area VARCHAR(50) DEFAULT 'collaboratori'"))


_ensure_new_columns()


def _ensure_new_enum_values():
    """Postgres ha un tipo enum nativo: aggiungere un valore richiede ALTER TYPE.
    Non serve su SQLite (locale), dove l'enum non è un tipo a parte."""
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'superadmin'"))


_ensure_new_enum_values()

app = FastAPI(
    title="Magic Volley Adelfia ASD API",
    description="Backend per il sito e il pannello gestionale della società Magic Volley Adelfia ASD",
    version="1.1.0",
)

# CORS: in sviluppo permissivo, in produzione va restretto al dominio reale del sito.
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(staff.router)
app.include_router(matches.router)
app.include_router(news.router)
app.include_router(registrations.router)
app.include_router(sponsors.router)
app.include_router(guardian_auth.router)
app.include_router(gallery.router)
app.include_router(sitemap.router)
app.include_router(uploads.router)
app.include_router(documents.router)


@app.get("/api/health", tags=["Sistema"])
def health_check():
    return {"status": "ok", "service": "magic-volley-adelfia-api"}
