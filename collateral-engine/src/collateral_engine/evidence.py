"""Write-once store of evidence photos, addressed by their SHA-256."""

import re
from pathlib import Path

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class EvidenceStore:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def path_for(self, sha256: str) -> Path:
        if _SHA256_PATTERN.fullmatch(sha256) is None:
            raise ValueError(f"'{sha256}' is not a SHA-256 hex digest")
        return self._directory / sha256[:2] / sha256

    def save(self, sha256: str, content: bytes) -> Path:
        """Stores the photo once; a second upload of the same bytes leaves the file untouched."""
        path = self.path_for(sha256)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(content)
        return path

    def load(self, sha256: str) -> bytes:
        return self.path_for(sha256).read_bytes()
