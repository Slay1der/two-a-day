"""Plain JSON files committed back to the repo: the repo is the database."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

STATUSES = ["Shortlisted", "Applied", "Assessment", "Interview", "Offer", "Rejected", "Withdrawn"]


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.apps_path = self.root / "data" / "apps.json"
        self.seen_path = self.root / "data" / "seen.json"

    def _load(self, path: Path, default):
        if not path.exists():
            return default
        text = path.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else default

    def _save(self, path: Path, value) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def apps(self) -> list[dict]:
        return self._load(self.apps_path, [])

    def seen(self) -> set[str]:
        return set(self._load(self.seen_path, []))

    def mark_seen(self, keys) -> None:
        self._save(self.seen_path, sorted(self.seen() | set(keys)))

    def add(self, entry: dict) -> None:
        apps = self.apps()
        if any(a.get("key") == entry.get("key") for a in apps):
            return
        entry.setdefault("status", "Shortlisted")
        entry.setdefault("added", date.today().isoformat())
        entry.setdefault("applied", "")
        apps.append(entry)
        self._save(self.apps_path, apps)

    def set_status(self, key: str, status: str, on: date | None = None) -> dict:
        if status not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        apps = self.apps()
        for a in apps:
            if a.get("key") == key or a.get("key", "").startswith(key):
                a["status"] = status
                if status != "Shortlisted" and not a.get("applied"):
                    a["applied"] = (on or date.today()).isoformat()
                if status == "Shortlisted":
                    a["applied"] = ""
                self._save(self.apps_path, apps)
                return a
        raise KeyError(f"no application with key {key}")
