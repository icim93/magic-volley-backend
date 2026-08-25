"""
Script one-off da lanciare nella Shell di Render (ha già DATABASE_URL in ambiente),
DOPO che il deploy con il nuovo ruolo 'superadmin' è live.

Promuove un utente esistente a superadmin.

Uso:
    python promote_superadmin.py
"""
from app.database import SessionLocal
from app import models


def main():
    email = input("Email dell'utente da promuovere a superadmin: ").strip()

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"Nessun utente trovato con email '{email}'.")
            return

        user.role = models.UserRole.superadmin
        db.commit()
        print(f"'{email}' è ora superadmin.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
