# Magic Volley Adelfia — Backend API

Backend FastAPI per il sito e il pannello gestionale della società.

## Avvio in locale

```bash
python3 -m venv venv
source venv/bin/activate          # su Windows: venv\Scripts\activate
pip install -r requirements.txt

# Crea il primo utente amministratore (una sola volta)
python create_admin.py

# Avvia il server di sviluppo
uvicorn app.main:app --reload
```

Il server parte su `http://localhost:8000`. Documentazione interattiva (Swagger) su `http://localhost:8000/docs`.

## Struttura del progetto

```
app/
  main.py           -> punto di ingresso, monta tutti i router
  database.py        -> configurazione SQLAlchemy (SQLite in sviluppo)
  models.py           -> tabelle: Team, Player, Staff, Match, News, Registration, Sponsor, User
  schemas.py          -> validazione input/output (Pydantic)
  core/
    security.py       -> hashing password e JWT
    deps.py            -> dependency per proteggere le route (login richiesto / admin richiesto)
  routers/
    auth.py            -> login, creazione utenti staff/admin
    teams.py            -> CRUD squadre
    players.py          -> CRUD giocatrici
    staff.py             -> CRUD staff tecnico
    matches.py           -> calendario e risultati
    news.py               -> blog/news
    registrations.py     -> form iscrizioni (pubblico) + gestione (staff)
    sponsors.py           -> CRUD sponsor
```

## Note sulle autorizzazioni

- **Pubblico (nessun login)**: lista squadre/giocatrici, calendario/risultati, news pubblicate, lista sponsor, invio form iscrizione.
- **Richiede login (staff o admin)**: creazione/modifica news, gestione iscrizioni ricevute.
- **Richiede login admin**: gestione squadre, giocatrici, staff tecnico, partite, sponsor, creazione nuovi utenti staff.

## Passaggio a produzione

1. Cambia `SECRET_KEY` in `.env` (vedi `.env.example`) con una stringa lunga e casuale.
2. Per un traffico più serio, valuta PostgreSQL invece di SQLite: basta impostare `DATABASE_URL` nel `.env`, il codice non cambia.
3. Imposta `ALLOWED_ORIGINS` con il dominio reale del sito (es. `https://magicvolleyadelfia.it`).
4. Deploy consigliato: Render (backend) + Vercel (frontend React).

## Prossimo passo

Il frontend React pubblico + pannello admin, che consumerà queste API.
