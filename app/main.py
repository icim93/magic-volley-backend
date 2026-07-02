"""
Entry point dell'applicazione Magic Volley Adelfia - Backend API.

Avvio in locale:
    uvicorn app.main:app --reload

Documentazione interattiva disponibile su /docs (Swagger) una volta avviato.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import auth, teams, players, staff, matches, news, registrations, sponsors

# Crea le tabelle nel DB se non esistono già.
# Per modifiche allo schema in futuro conviene passare ad Alembic (già incluso nei requirements).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Magic Volley Adelfia API",
    description="Backend per il sito e il pannello gestionale della società Magic Volley Adelfia",
    version="1.0.0",
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


@app.get("/api/health", tags=["Sistema"])
def health_check():
    return {"status": "ok", "service": "magic-volley-adelfia-api"}
