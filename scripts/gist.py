import hashlib
import json
import os
import sqlite3

import requests
from dotenv import load_dotenv

DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "gists.db")
)


def get_gist_url(stylename: str, source: str, db_path: str | None = None) -> str:
    """Create or reuse a GitHub Gist for a given Python source style."""
    load_dotenv()  # Load GitHub token from .env
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise RuntimeError("Missing GITHUB_TOKEN in .env file")

    DESC = "Python script to create artistic looking image"
    API_URL = "https://api.github.com/gists"

    db_path = os.path.abspath(db_path or DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        # --- setup db ---
        conn.execute(
            """CREATE TABLE IF NOT EXISTS gists (
            stylename TEXT PRIMARY KEY,
            hash TEXT,
            url TEXT
        )"""
        )

        # --- compute hash ---
        src_hash = hashlib.sha256(source.encode()).hexdigest()
        row = conn.execute(
            "SELECT hash, url FROM gists WHERE stylename=?", (stylename,)
        ).fetchone()

        # --- reuse if unchanged ---
        if row and row[0] == src_hash:
            return row[1]

        # --- create gist ---
        headers = {"Authorization": f"token {github_token}"}
        payload = {
            "description": DESC,
            "public": True,
            "files": {f"{stylename}.py": {"content": source}},
        }
        r = requests.post(API_URL, headers=headers, data=json.dumps(payload))
        r.raise_for_status()
        gist_url = r.json()["html_url"]

        # --- save or update record ---
        conn.execute(
            "REPLACE INTO gists (stylename, hash, url) VALUES (?, ?, ?)",
            (stylename, src_hash, gist_url),
        )
        conn.commit()

        return gist_url
    finally:
        conn.close()
