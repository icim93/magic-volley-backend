"""
Genera sitemap.xml al volo, includendo le pagine statiche pubbliche più
ogni news pubblicata e ogni giocatrice attiva. Non richiede autenticazione:
è un endpoint pubblico, come robots.txt.
"""
import os
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(tags=["Sitemap"])

PUBLIC_SITE_URL = os.getenv("PUBLIC_SITE_URL", "https://www.magicvolleyadelfia.it").rstrip("/")

STATIC_PATHS = [
    "/", "/societa", "/squadre", "/calendario", "/news",
    "/gallery", "/sponsor", "/contatti", "/iscriviti",
]


def _url_entry(path: str) -> str:
    return f"  <url>\n    <loc>{escape(PUBLIC_SITE_URL + path)}</loc>\n  </url>"


@router.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    entries = [_url_entry(p) for p in STATIC_PATHS]

    published_news = (
        db.query(models.News.slug).filter(models.News.published == True).all()  # noqa: E712
    )
    entries += [_url_entry(f"/news/{slug}") for (slug,) in published_news]

    active_teams = (
        db.query(models.Team.id).filter(models.Team.is_active == True).all()  # noqa: E712
    )
    entries += [_url_entry(f"/squadre/{team_id}") for (team_id,) in active_teams]

    active_players = (
        db.query(models.Player.id).filter(models.Player.is_active == True).all()  # noqa: E712
    )
    entries += [_url_entry(f"/giocatrici/{player_id}") for (player_id,) in active_players]

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>"
    )
    return Response(content=xml, media_type="application/xml")
