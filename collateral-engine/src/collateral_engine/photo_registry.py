"""Which application each photo came with, to catch the same photo reused across applications."""

import sqlite3
from pathlib import Path

from collateral_engine.photos import hamming_distance


class PhotoRegistry:
    def __init__(self, path: Path) -> None:
        self._path = path
        with sqlite3.connect(self._path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS photos(
                    application_id TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    difference_hash TEXT NOT NULL,
                    PRIMARY KEY (application_id, sha256))"""
            )

    def register(self, application_id: str, sha256: str, difference_hash: int) -> None:
        with sqlite3.connect(self._path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO photos VALUES (?, ?, ?)",
                (application_id, sha256, f"{difference_hash:016x}"),
            )

    def applications_with_similar_photo(
        self, difference_hash: int, max_hamming: int, excluded_application_id: str
    ) -> list[str]:
        with sqlite3.connect(self._path) as connection:
            rows = connection.execute(
                "SELECT application_id, difference_hash FROM photos WHERE application_id != ?",
                (excluded_application_id,),
            ).fetchall()
        return sorted(
            {
                application_id
                for application_id, stored_hash in rows
                if hamming_distance(difference_hash, int(stored_hash, 16)) <= max_hamming
            }
        )
