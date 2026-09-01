import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.deps import get_current_guardian
from app.core.push import VAPID_PUBLIC_KEY, send_push_to_guardians

router = APIRouter(prefix="/api/push", tags=["Notifiche push"])

CRON_SECRET = os.getenv("CRON_SECRET")


@router.get("/vapid-public-key")
def get_vapid_public_key():
    """Pubblica per design (serve al frontend prima ancora di autenticarsi come genitore)."""
    return {"public_key": VAPID_PUBLIC_KEY}


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe(
    data: schemas.PushSubscriptionCreate,
    guardian: models.Guardian = Depends(get_current_guardian),
    db: Session = Depends(get_db),
):
    """Registra (o aggiorna) l'iscrizione alle notifiche per questo dispositivo."""
    existing = db.query(models.PushSubscription).filter(models.PushSubscription.endpoint == data.endpoint).first()
    if existing:
        # Stesso endpoint già noto: capita se un dispositivo condiviso passa da un
        # account genitore all'altro, o se il genitore ha rifatto login. Riassegna.
        existing.guardian_id = guardian.id
        existing.p256dh_key = data.keys.p256dh
        existing.auth_key = data.keys.auth
        existing.user_agent = data.user_agent
        existing.last_used_at = datetime.utcnow()
    else:
        db.add(models.PushSubscription(
            guardian_id=guardian.id,
            endpoint=data.endpoint,
            p256dh_key=data.keys.p256dh,
            auth_key=data.keys.auth,
            user_agent=data.user_agent,
        ))
    db.commit()
    return {"message": "Notifiche attivate."}


@router.delete("/subscribe")
def unsubscribe(
    endpoint: str,
    guardian: models.Guardian = Depends(get_current_guardian),
    db: Session = Depends(get_db),
):
    """Cancella l'iscrizione di questo dispositivo — solo se appartiene al genitore loggato."""
    sub = (
        db.query(models.PushSubscription)
        .filter(models.PushSubscription.endpoint == endpoint, models.PushSubscription.guardian_id == guardian.id)
        .first()
    )
    if sub:
        db.delete(sub)
        db.commit()
    return {"message": "Notifiche disattivate."}


@router.post("/send-match-reminders")
def send_match_reminders(x_cron_secret: str = Header(default=None), db: Session = Depends(get_db)):
    """
    Chiamata da un job schedulato esterno (non da un utente loggato), protetta
    da un secret condiviso invece che da un account — vedi CRON_SECRET.
    Manda un promemoria per le partite programmate tra 23 e 25 ore da adesso,
    una sola volta per partita (reminder_sent).
    """
    if not CRON_SECRET or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non autorizzato.")

    now = datetime.utcnow()
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)

    matches = (
        db.query(models.Match)
        .filter(
            models.Match.status == models.MatchStatus.scheduled,
            models.Match.match_date >= window_start,
            models.Match.match_date <= window_end,
            models.Match.reminder_sent.is_(False),
        )
        .all()
    )

    sent_count = 0
    for match in matches:
        player_ids_query = db.query(models.Player.id).filter(models.Player.team_id == match.home_team_id)
        guardians = (
            db.query(models.Guardian)
            .join(models.guardian_player_association)
            .filter(models.guardian_player_association.c.player_id.in_(player_ids_query))
            .all()
        )
        guardian_ids = {g.id for g in guardians}
        if guardian_ids:
            body = match.match_date.strftime('%d/%m alle %H:%M')
            if match.location:
                body += f" — {match.location}"
            send_push_to_guardians(
                db,
                guardian_ids,
                title=f"Promemoria: {match.home_team_name} vs {match.away_team_name}",
                body=body,
                url="/area-riservata",
            )
        match.reminder_sent = True
        sent_count += 1
    db.commit()

    return {"matches_notified": sent_count}
