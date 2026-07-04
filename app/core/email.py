"""
Invio email transazionali (attivazione account genitori).

Usa Resend (https://resend.com) se RESEND_API_KEY è impostata nelle variabili
d'ambiente. Se non è configurata, l'email non viene realmente inviata ma la
funzione non fallisce: l'operazione che l'ha richiesta (es. approvare
un'iscrizione) va comunque a buon fine, e il link di attivazione viene
restituito nella risposta dell'API così lo staff può copiarlo e inviarlo a
mano nel frattempo. Questo evita di bloccare il lavoro dello staff prima che
Resend sia collegato.
"""
import os
import httpx

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "Magic Volley Adelfia <onboarding@resend.dev>")


def send_activation_email(to_email: str, first_name: str, activation_link: str) -> bool:
    """
    Ritorna True se l'email è stata effettivamente inviata, False se è stata
    solo "simulata" (Resend non configurato) o se l'invio è fallito.
    In entrambi i casi non solleva eccezioni: l'invio email non deve mai
    bloccare il flusso di approvazione dell'iscrizione.
    """
    if not RESEND_API_KEY:
        print(f"[EMAIL NON INVIATA - Resend non configurato] Link di attivazione per {to_email}: {activation_link}")
        return False

    subject = "Attiva il tuo account — Magic Volley Adelfia"
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <p>Ciao {first_name},</p>
      <p>La tua richiesta di iscrizione è stata approvata da Magic Volley Adelfia.
      Attiva il tuo account per accedere all'area riservata (pagamenti, calendario, comunicazioni):</p>
      <p style="text-align:center; margin: 24px 0;">
        <a href="{activation_link}" style="background:#F2A93B; color:#14213D; padding:12px 24px;
           text-decoration:none; border-radius:999px; font-weight:bold;">Attiva il tuo account</a>
      </p>
      <p style="font-size: 12px; color: #666;">
        Se il pulsante non funziona, copia questo link nel browser:<br>{activation_link}
      </p>
    </div>
    """
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={"from": EMAIL_FROM, "to": [to_email], "subject": subject, "html": html},
            timeout=10.0,
        )
        return response.status_code < 300
    except httpx.HTTPError:
        print(f"[ERRORE INVIO EMAIL] Link di attivazione per {to_email}: {activation_link}")
        return False
