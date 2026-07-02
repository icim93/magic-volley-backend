"""
Script da lanciare UNA VOLTA per creare il primo utente amministratore.
Necessario perché l'endpoint POST /api/auth/users richiede già un admin loggato
(giusto motivo: nessuno deve poter auto-registrarsi come admin dal sito pubblico).

Uso:
    python create_admin.py
"""
import getpass
from app.database import SessionLocal, engine, Base
from app import models
from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)


def main():
    db = SessionLocal()
    try:
        email = input("Email admin: ").strip()
        existing = db.query(models.User).filter(models.User.email == email).first()
        if existing:
            print(f"Esiste già un utente con questa email (ruolo: {existing.role.value}).")
            return

        full_name = input("Nome e cognome: ").strip()
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Conferma password: ")

        if password != password_confirm:
            print("Le password non coincidono. Riprova.")
            return

        admin = models.User(
            email=email,
            full_name=full_name,
            role=models.UserRole.admin,
            hashed_password=get_password_hash(password),
        )
        db.add(admin)
        db.commit()
        print(f"Utente admin '{email}' creato correttamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
