"""
Script one-off per caricare i PDF originali (Statuto, Regolamento, MOG,
polizze assicurative) su Supabase Storage tramite l'API di produzione, così
il sito può linkarli come "documento originale" per chi vuole verificare.

Scrive gli URL ottenuti in document_urls.json nella stessa cartella dei file,
così Claude può leggerli direttamente senza che tu debba ricopiarli a mano.

Uso:
    python upload_source_documents.py
"""
import getpass
import json
import os

import httpx

API_URL = "https://magic-volley-backend.onrender.com"
STATUTI_DIR = r"C:\Users\user\Desktop\Sito magic volley\Statuti"
SCRATCH_DIR = r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-Sito-magic-volley\2b0ad00e-ff05-47d8-a286-87c3ad9229de\scratchpad\statuto_compressed"

FILES = [
    ("statuto", os.path.join(SCRATCH_DIR, "Statuto-compresso.pdf"), "application/pdf"),
    ("regolamento", os.path.join(STATUTI_DIR, "Regolamento associativo.pdf"), "application/pdf"),
    ("safeguarding", os.path.join(STATUTI_DIR, "MOG DELIBERATO PDF.pdf"), "application/pdf"),
    ("polizza_csen", os.path.join(STATUTI_DIR, "Polizza CSEN.pdf"), "application/pdf"),
    ("polizza_fipav", os.path.join(STATUTI_DIR, "Polizza FIPAV.pdf"), "application/pdf"),
]


def main():
    print(f"API di produzione: {API_URL}")
    username = input("Username admin: ").strip()
    password = getpass.getpass("Password admin: ")

    with httpx.Client(base_url=API_URL, timeout=60) as client:
        login_resp = client.post("/api/auth/login", data={"username": username, "password": password})
        if login_resp.status_code != 200:
            print(f"Login fallito ({login_resp.status_code}): {login_resp.text}")
            return
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        urls = {}
        for key, path, content_type in FILES:
            if not os.path.exists(path):
                print(f"Saltato {key}: file non trovato ({path})")
                continue
            with open(path, "rb") as f:
                resp = client.post(
                    "/api/uploads",
                    params={"folder": "documenti-originali"},
                    files={"file": (os.path.basename(path), f, content_type)},
                    headers=headers,
                )
            if resp.status_code == 200:
                url = resp.json()["url"]
                urls[key] = url
                print(f"Caricato {key}: {url}")
            else:
                print(f"Errore su {key} ({resp.status_code}): {resp.text}")

        out_path = os.path.join(STATUTI_DIR, "document_urls.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(urls, f, indent=2, ensure_ascii=False)
        print(f"\nURL salvati in {out_path}")


if __name__ == "__main__":
    main()
