"""
convlog.py — trajno beleženje pogovorov za statistiko (SpoznajAI bot-stats).

Vsak par (uporabnikovo sporočilo → botov odgovor) se shrani v SQLite.
Bere ga admin endpoint /api/admin/conversations, ki ga vsako uro pobira
zunanji zbiralnik statistike na strežniku.

Načelo: pisanje je "best-effort" — če karkoli spodleti, se napaka samo
izpiše, klepet pa deluje naprej brez motenj.

Kje se shrani: če je na Railwayu pripet trajni disk (volume), piše tja in
podatki preživijo ponovne deploye; sicer lokalno (podatke med deployi
pobere urni zbiralnik, zato statistika ni prizadeta).
"""
from __future__ import annotations

import os
import sqlite3
import time
import datetime
import threading
from pathlib import Path

_LOCK = threading.Lock()


def _db_path() -> str:
    base = (
        os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
        or os.environ.get("DATA_DIR")
        or str(Path(__file__).resolve().parents[2])   # koren repozitorija
    )
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        base = str(Path(__file__).resolve().parents[2])
    return os.path.join(base, "conversations.db")


_PATH = _db_path()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_PATH, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute(
        """CREATE TABLE IF NOT EXISTS conversations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT,
            created_at   TEXT,
            ts           INTEGER,
            user_message TEXT,
            bot_response TEXT
        )"""
    )
    c.execute("CREATE INDEX IF NOT EXISTS ix_conv_ts ON conversations(ts)")
    return c


def log_exchange(session_id: str, user_message: str, bot_response: str) -> None:
    """Shrani en par pogovora. Nikoli ne vrže napake navzven."""
    try:
        now = time.time()
        iso = datetime.datetime.utcfromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        with _LOCK:
            c = _conn()
            try:
                c.execute(
                    "INSERT INTO conversations "
                    "(session_id, created_at, ts, user_message, bot_response) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (session_id or "", iso, int(now),
                     user_message or "", bot_response or ""),
                )
                c.commit()
            finally:
                c.close()
    except Exception as e:  # beleženje nikoli ne sme podreti klepeta
        print(f"[convlog] napaka pri shranjevanju: {e}", flush=True)


def fetch(hours: int = 25, limit: int = 5000) -> list[dict]:
    """Vrne pogovore iz zadnjih 'hours' ur (največ 'limit' vrstic)."""
    try:
        hours = max(1, int(hours))
        limit = max(1, min(int(limit), 100000))
        meja = int(time.time()) - hours * 3600
        with _LOCK:
            c = _conn()
            try:
                rows = c.execute(
                    "SELECT session_id, created_at, ts, user_message, bot_response "
                    "FROM conversations WHERE ts >= ? ORDER BY ts ASC LIMIT ?",
                    (meja, limit),
                ).fetchall()
            finally:
                c.close()
        return [
            {
                "session_id": r[0],
                "created_at": r[1],
                "ts": r[2],
                "user_message": r[3],
                "bot_response": r[4],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[convlog] napaka pri branju: {e}", flush=True)
        return []
