"""
Invio notifiche push web (Web Push standard, VAPID) ai genitori/atlete con
account nell'area riservata.

Stesso schema di app/core/email.py: legge la configurazione dalle variabili
d'ambiente, non solleva mai eccezioni verso il chiamante (l'invio push è
sempre un effetto collaterale "a parte" rispetto all'operazione principale:
pubblicare una news o salvare un risultato non deve mai fallire per colpa
di una notifica non andata a buon fine), logga e continua sul prossimo
destinatario in caso di errore.
"""
import os
from typing import Iterable

from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session

from app import models

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_CLAIMS_SUBJECT = os.getenv("VAPID_CLAIMS_SUBJECT", "mailto:info@magicvolleyadelfia.it")


def _send_to_subscription(sub: "models.PushSubscription", title: str, body: str, url: str | None) -> str:
    """Ritorna 'sent', 'expired' (subscription da cancellare) o 'error' (transitorio, si riprova al prossimo invio). Non solleva mai."""
    import json

    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh_key, "auth": sub.auth_key},
            },
            data=json.dumps({"title": title, "body": body, "url": url or "/"}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_CLAIMS_SUBJECT},
            ttl=60 * 60 * 24,
        )
        return "sent"
    except WebPushException as exc:
        if exc.status_code in (404, 410):
            # Dispositivo disinstallato o permesso revocato: la subscription non serve più.
            return "expired"
        print(f"[PUSH] Invio fallito per subscription {sub.id}: {exc}")
        return "error"
    except Exception as exc:  # difesa extra: un push non deve mai far cadere il chiamante
        print(f"[PUSH] Errore imprevisto per subscription {sub.id}: {exc}")
        return "error"


def send_push_to_guardians(db: Session, guardian_ids: Iterable[int], title: str, body: str, url: str | None = None) -> None:
    """Manda una notifica a tutte le subscription dei genitori indicati (dedup automatico)."""
    if not VAPID_PRIVATE_KEY:
        print(f"[PUSH NON INVIATA - VAPID non configurato] {title}: {body}")
        return

    guardian_ids = {gid for gid in guardian_ids if gid is not None}
    if not guardian_ids:
        return

    subs = db.query(models.PushSubscription).filter(models.PushSubscription.guardian_id.in_(guardian_ids)).all()
    _send_and_prune(db, subs, title, body, url)


def send_push_to_all_guardians(db: Session, title: str, body: str, url: str | None = None) -> None:
    """Manda una notifica a tutti i genitori/atlete che hanno almeno un dispositivo iscritto (es. news pubblicata)."""
    if not VAPID_PRIVATE_KEY:
        print(f"[PUSH NON INVIATA - VAPID non configurato] {title}: {body}")
        return

    subs = db.query(models.PushSubscription).all()
    _send_and_prune(db, subs, title, body, url)


def _send_and_prune(db: Session, subs: list, title: str, body: str, url: str | None) -> None:
    from datetime import datetime

    for sub in subs:
        result = _send_to_subscription(sub, title, body, url)
        if result == "sent":
            sub.last_used_at = datetime.utcnow()
        elif result == "expired":
            db.delete(sub)
        # "error": transitorio, la subscription resta, si riprova al prossimo invio
    db.commit()
