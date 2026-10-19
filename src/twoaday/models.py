from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field

_TAGS = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    import html

    return _SPACE.sub(" ", _TAGS.sub(" ", html.unescape(text or ""))).strip()


@dataclass
class Job:
    source: str
    company: str
    title: str
    url: str
    locations: list[str] = field(default_factory=list)
    description: str = ""
    deadline: str = ""
    posted: str = ""
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        raw = f"{self.company.lower()}|{self.title.lower()}|{self.url}"
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    @property
    def location_text(self) -> str:
        return " / ".join(self.locations) or "Not stated"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["key"] = self.key
        d.pop("description")
        return d
