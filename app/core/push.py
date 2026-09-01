"""
Invio notifiche push web (Web Push standard, VAPID) ai genitori/atlete con
account nell'area riservata, con relativa cronologia (Notification) così che
il "report notifiche" nell'area riservata non dipenda dalla notifica del
sistema operativo, che sparisce non appena vista.

Stesso schema di app/core/email.py: legge la configurazione dalle variabili
d'ambiente, non solleva mai eccezioni verso il chiamante (l'invio push è
sempre un effetto collaterale "a parte" rispetto all'operazione principale:
pubblicare una news o salvare un risultato non deve mai fallire per colpa
di una notifica non andata a buon fine), logga e continua sul prossimo
destinatario in caso di errore.
"""
import os
from datetime import datetime
from typing import Iterable

from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session

from app import models

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_CLAIMS_SUBJECT = os.getenv("VAPID_CLAIMS_SUBJECT", "mailto:info@magicvolleyadelfia.it")

# Categorie di notifica che il genitore può disattivare singolarmente
# (vedi Guardian.notify_* in models.py). Un messaggio diretto dello staff
# (send_direct_message) non passa da questo filtro apposta.
_CATEGORY_COLUMNS = {
    "news": "notify_news",
    "match_results": "notify_match_results",
    "match_reminders": "notify_match_reminders",
}


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


def _filter_by_category(db: Session, guardian_ids: set[int], category: str | None) -> set[int]:
    if not category or not guardian_ids:
        return guardian_ids
    column_name = _CATEGORY_COLUMNS[category]
    rows = (
        db.query(models.Guardian.id)
        .filter(models.Guardian.id.in_(guardian_ids), getattr(models.Guardian, column_name).is_(True))
        .all()
    )
    return {r[0] for r in rows}


def _log_notifications(db: Session, guardian_ids: Iterable[int], title: str, body: str, url: str | None) -> None:
    """Cronologia in-app: scritta per il pubblico finale (già filtrato per preferenza),
    a prescindere dal fatto che quel genitore abbia o meno un dispositivo push iscritto —
    così la vede comunque quando entra nell'area riservata."""
    for gid in guardian_ids:
        db.add(models.Notification(guardian_id=gid, title=title, body=body, url=url))


def send_push_to_guardians(
    db: Session, guardian_ids: Iterable[int], title: str, body: str, url: str | None = None, category: str | None = None
) -> None:
    """Notifica i genitori indicati: scrive comunque la cronologia, e se possibile manda anche la push.
    Se "category" è indicata, rispetta la preferenza del genitore per quella categoria (per entrambe)."""
    guardian_ids = {gid for gid in guardian_ids if gid is not None}
    guardian_ids = _filter_by_category(db, guardian_ids, category)
    if not guardian_ids:
        return

    _log_notifications(db, guardian_ids, title, body, url)

    if not VAPID_PRIVATE_KEY:
        db.commit()
        print(f"[PUSH NON INVIATA - VAPID non configurato] {title}: {body}")
        return

    subs = db.query(models.PushSubscription).filter(models.PushSubscription.guardian_id.in_(guardian_ids)).all()
    _send_and_prune(db, subs, title, body, url)


def send_push_to_all_guardians(db: Session, title: str, body: str, url: str | None = None, category: str | None = None) -> None:
    """Notifica tutti i genitori/atlete attivi (es. news pubblicata) — non solo chi ha un dispositivo iscritto."""
    guardian_ids = {r[0] for r in db.query(models.Guardian.id).filter(models.Guardian.is_active.is_(True)).all()}
    send_push_to_guardians(db, guardian_ids, title, body, url, category)


def has_active_push_subscription(db: Session, guardian_id: int) -> bool:
    return (
        db.query(models.PushSubscription.id)
        .filter(models.PushSubscription.guardian_id == guardian_id)
        .first()
        is not None
    )


def send_direct_message(db: Session, guardian_id: int, title: str, body: str, url: str | None = None) -> bool:
    """
    Messaggio diretto dello staff a UN genitore (es. "assente oggi"): non passa
    dalle preferenze di categoria, è sempre un contatto voluto esplicitamente.
    Scrive comunque la cronologia. Ritorna True se c'era almeno una subscription
    su cui tentare l'invio push (non garantisce la consegna effettiva — il
    chiamante decide se usare l'email come alternativa in base a questo).
    """
    _log_notifications(db, [guardian_id], title, body, url)

    if not VAPID_PRIVATE_KEY:
        db.commit()
        return False
    subs = db.query(models.PushSubscription).filter(models.PushSubscription.guardian_id == guardian_id).all()
    if not subs:
        db.commit()
        return False
    _send_and_prune(db, subs, title, body, url)
    return True


def _send_and_prune(db: Session, subs: list, title: str, body: str, url: str | None) -> None:
    for sub in subs:
        result = _send_to_subscription(sub, title, body, url)
        if result == "sent":
            sub.last_used_at = datetime.utcnow()
        elif result == "expired":
            db.delete(sub)
        # "error": transitorio, la subscription resta, si riprova al prossimo invio
    db.commit()
