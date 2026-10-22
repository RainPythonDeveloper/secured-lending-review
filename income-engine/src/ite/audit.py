"""Tamper-evident audit log: each record stores the hash of the previous one (hash chain).

Changing or deleting any past decision breaks the chain, which verify() detects.
SQLite here; the same design maps to PostgreSQL or an append-only object store in production.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS decisions(
                seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL UNIQUE, payload TEXT NOT NULL)""")

    @staticmethod
    def _digest(prev: str, ts: str, payload: str) -> str:
        return hashlib.sha256(f"{prev}|{ts}|{payload}".encode()).hexdigest()

    def append(self, record: dict) -> str:
        payload = json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with sqlite3.connect(self.path) as c:
            row = c.execute("SELECT hash FROM decisions ORDER BY seq DESC LIMIT 1").fetchone()
            prev = row[0] if row else GENESIS
            h = self._digest(prev, ts, payload)
            c.execute("INSERT INTO decisions(ts, prev_hash, hash, payload) VALUES (?,?,?,?)", (ts, prev, h, payload))
        return h

    def records(self, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.path) as c:
            rows = c.execute("SELECT seq, ts, hash, payload FROM decisions ORDER BY seq DESC LIMIT ?", (limit,)).fetchall()
        return [{"seq": s, "ts": t, "hash": h, **json.loads(p)} for s, t, h, p in rows]

    def verify(self) -> tuple[bool, int]:
        """Returns (chain intact, number of records checked)."""
        with sqlite3.connect(self.path) as c:
            rows = c.execute("SELECT ts, prev_hash, hash, payload FROM decisions ORDER BY seq").fetchall()
        prev = GENESIS
        for ts, p, h, payload in rows:
            if p != prev or self._digest(p, ts, payload) != h:
                return False, len(rows)
            prev = h
        return True, len(rows)
