"""
Script one-off per promuovere un utente a superadmin quando non hai accesso
alla Shell di Render (es. piano gratuito).

Prima di lanciarlo:
1. Su Render → magic-volley-backend → Environment: aggiungi una env var
   BOOTSTRAP_TOKEN con un valore lungo e casuale a tua scelta.
2. Fai un deploy (manuale se l'auto-deploy non parte da solo) così la env var
   viene caricata.
3. Lancia questo script e inserisci lo stesso valore di BOOTSTRAP_TOKEN.
4. Dopo l'uso, torna su Render e RIMUOVI la env var BOOTSTRAP_TOKEN
   (senza di essa l'endpoint resta comunque disattivato).

Uso:
    python bootstrap_superadmin.py
"""
import getpass

import httpx

API_URL = "https://magic-volley-backend.onrender.com"


def main():
    print(f"API di produzione: {API_URL}")
    email = input("Email da promuovere a superadmin: ").strip()
    token = getpass.getpass("BOOTSTRAP_TOKEN (quello impostato su Render): ")

    with httpx.Client(base_url=API_URL, timeout=15) as client:
        resp = client.post(
            "/api/auth/bootstrap-superadmin",
            json={"email": email, "token": token},
        )
        if resp.status_code == 200:
            print(resp.json()["message"])
        else:
            print(f"Errore ({resp.status_code}): {resp.text}")


if __name__ == "__main__":
    main()
