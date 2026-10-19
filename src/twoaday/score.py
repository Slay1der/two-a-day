from __future__ import annotations

import re
from datetime import date

from .models import Job


def _rx(words: list[str]) -> re.Pattern | None:
    words = [w for w in words or [] if w]
    if not words:
        return None
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)


class Scorer:
    def __init__(self, profile: dict, today: date | None = None):
        self.p = profile
        self.today = today or date.today()
        self.include = _rx(profile.get("title_include", []))
        self.exclude = _rx(profile.get("title_exclude", []))
        self.allow = [x.lower() for x in profile.get("locations_allow", [])]
        self.desc_exclude = [x.lower() for x in profile.get("description_exclude", [])]
        self.keywords = {k.lower(): float(v) for k, v in (profile.get("keywords") or {}).items()}

    def eligible(self, job: Job) -> tuple[bool, str]:
        if self.include and not self.include.search(job.title):
            return False, "title is not an early-career role"
        if self.exclude and self.exclude.search(job.title):
            return False, "title is too senior"
        if self.allow:
            locs = " ".join(job.locations).lower()
            if not locs or not any(a in locs for a in self.allow):
                return False, f"location not workable ({job.location_text})"
        desc = job.description.lower()
        for phrase in self.desc_exclude:
            if phrase in desc:
                return False, f"description says '{phrase}'"
        if job.deadline:
            try:
                if date.fromisoformat(job.deadline) < self.today:
                    return False, "deadline passed"
            except ValueError:
                pass
        return True, ""

    def score(self, job: Job) -> Job:
        title = job.title.lower()
        text = f"{title} {job.description.lower()}"
        total, reasons = 0.0, []
        for kw, weight in self.keywords.items():
            pattern = re.compile(r"\b" + re.escape(kw) + r"\b")
            hits = len(pattern.findall(text))
            if not hits:
                continue
            gained = weight * (2 if pattern.search(title) else 1) + min(hits - 1, 3) * 0.5
            total += gained
            reasons.append(kw)
        if job.deadline:
            try:
                days = (date.fromisoformat(job.deadline) - self.today).days
                if 0 <= days <= 14:
                    total += 3
                    reasons.append(f"closes in {days}d")
            except ValueError:
                pass
        job.score = round(total, 2)
        job.reasons = reasons[:6]
        return job

    def pick(self, jobs: list[Job], seen: set[str], n: int) -> list[Job]:
        ranked = []
        for job in jobs:
            if job.key in seen:
                continue
            ok, _ = self.eligible(job)
            if ok:
                ranked.append(self.score(job))
        ranked = [j for j in ranked if j.score > 0]
        ranked.sort(key=lambda j: j.score, reverse=True)
        chosen, companies = [], set()
        for job in ranked:
            if job.company.lower() in companies:
                continue
            chosen.append(job)
            companies.add(job.company.lower())
            if len(chosen) == n:
                break
        return chosen
