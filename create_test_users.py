"""
Script da lanciare UNA TANTUM per creare gli utenti di prova sul pannello gestionale
in produzione. Usa un account admin già esistente per autenticarsi e poi chiama
POST /api/auth/users per ciascun nuovo utente (stessa API usata dal pannello).

Non serve accesso al database di produzione: passa solo dall'API pubblica via HTTPS.

Uso:
    python create_test_users.py
"""
import getpass

import httpx

API_URL = "https://magic-volley-backend.onrender.com"

# Password provvisoria uguale per tutti, da cambiare al primo accesso (Profilo > Cambia password).
PROVISIONAL_PASSWORD = "123456"

TEST_USERS = [
    {"email": "giovanni", "full_name": "Giovanni", "role": "staff"},
    {"email": "annalisa", "full_name": "Annalisa", "role": "staff"},
    {"email": "marco", "full_name": "Marco", "role": "admin"},
    {"email": "angela", "full_name": "Angela", "role": "admin"},
]


def main():
    print(f"API di produzione: {API_URL}")
    admin_username = input("Username admin esistente: ").strip()
    admin_password = getpass.getpass("Password admin: ")

    with httpx.Client(base_url=API_URL, timeout=15) as client:
        login_resp = client.post(
            "/api/auth/login",
            data={"username": admin_username, "password": admin_password},
        )
        if login_resp.status_code != 200:
            print(f"Login admin fallito ({login_resp.status_code}): {login_resp.text}")
            return

        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print()
        created = []
        for u in TEST_USERS:
            resp = client.post(
                "/api/auth/users",
                json={
                    "email": u["email"],
                    "full_name": u["full_name"],
                    "role": u["role"],
                    "password": PROVISIONAL_PASSWORD,
                },
                headers=headers,
            )
            if resp.status_code == 201:
                print(f"Creato: {u['email']} ({u['role']})")
                created.append(u)
            elif resp.status_code == 400:
                print(f"Saltato {u['email']}: esiste già.")
            else:
                print(f"Errore su {u['email']} ({resp.status_code}): {resp.text}")

        if created:
            print("\nCredenziali da comunicare (password provvisoria, da cambiare al primo accesso):")
            for u in created:
                print(f"  - {u['email']} / {PROVISIONAL_PASSWORD}  [{u['role']}]")


if __name__ == "__main__":
    main()
