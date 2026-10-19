"""Tailor the base CV to one posting with Claude, then refuse anything that adds facts."""

from __future__ import annotations

import logging
import os
import re
from types import SimpleNamespace

from .models import Job

log = logging.getLogger(__name__)
DEFAULT_MODEL = os.environ.get("TWOADAY_MODEL", "claude-sonnet-5-5")

SYSTEM = """You tailor a one-page LaTeX CV (Jake's Resume template) to a specific job posting.
Rules, all mandatory:
- Output ONLY the complete LaTeX document, from \\documentclass to \\end{document}. No commentary, no code fences.
- Keep the preamble, custom commands and section structure exactly as given.
- You may reorder bullets and sections, rephrase bullets using the posting's vocabulary, and reorder or trim
  skills. You may drop weaker bullets to keep one page.
- NEVER add an employer, project, certification, tool, number, metric or date that is not already in the CV.
- Keep every name, link, phone number and email exactly as written."""

PROMPT = """JOB POSTING
Company: {company}
Title: {title}
Location: {location}
Description:
{description}

BASE CV (LaTeX):
{tex}"""

_NUM = re.compile(r"\d+(?:[.,]\d+)?\+?%?")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]{2,}")
_ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]{1,}\b")


def _body(tex: str) -> str:
    start = tex.find(r"\begin{document}")
    return tex[start:] if start >= 0 else tex


def new_facts(base: str, tailored: str) -> list[str]:
    """Numbers and capitalised terms (tools, certs, employers) present in tailored but not base."""
    b, t = _body(base), _body(tailored)
    b_lower = b.lower()
    added = {n for n in _NUM.findall(t) if n not in b}
    for w in _ACRONYM.findall(t):
        if w.lower() not in b_lower:
            added.add(w)
    for w in _WORD.findall(t):
        if w[0].isupper() and w.lower() not in b_lower and not w.startswith("\\"):
            added.add(w)
    return sorted(added)


def _clean(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiClient:
    """Minimal Gemini REST client (free tier works). Same .messages.create shape as the Anthropic SDK."""

    def __init__(self, api_key: str, model: str = GEMINI_MODEL):
        self.api_key, self.model = api_key, model
        self.messages = self

    def create(self, *, system: str, messages: list[dict], max_tokens: int = 8000, **_):
        import requests

        resp = requests.post(
            GEMINI_URL.format(model=self.model),
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": m["content"]}]} for m in messages],
                "generationConfig": {"maxOutputTokens": max(max_tokens, 16000), "temperature": 0.3},
            },
            timeout=120,
        )
        resp.raise_for_status()
        parts = resp.json()["candidates"][0]["content"]["parts"]
        return SimpleNamespace(content=[SimpleNamespace(text=p.get("text", "")) for p in parts])


def make_client():
    """Anthropic if ANTHROPIC_API_KEY is set, else Gemini if GEMINI_API_KEY is set, else None."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic

        return anthropic.Anthropic(), DEFAULT_MODEL
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiClient(os.environ["GEMINI_API_KEY"]), GEMINI_MODEL
    return None, ""


def tailor(base_tex: str, job: Job, client=None, model: str = DEFAULT_MODEL) -> tuple[str, str]:
    """Returns (tex, note). Falls back to the base CV when there is no API key or the guard trips."""
    if client is None:
        client, model = make_client()
        if client is None:
            return base_tex, "base CV (no ANTHROPIC_API_KEY or GEMINI_API_KEY set)"
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=8000,
            system=SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(
                        company=job.company,
                        title=job.title,
                        location=job.location_text,
                        description=job.description[:12000],
                        tex=base_tex,
                    ),
                }
            ],
        )
    except Exception as e:  # a model outage or quota hit must not stop the run
        log.warning("tailoring for %s failed: %s", job.company, e)
        return base_tex, f"base CV (tailoring failed: {type(e).__name__})"
    text = _clean("".join(getattr(b, "text", "") for b in msg.content))
    if r"\documentclass" not in text or r"\end{document}" not in text:
        return base_tex, "base CV (model output was not a full LaTeX document)"
    added = new_facts(base_tex, text)
    if added:
        log.warning("tailoring for %s added unverified terms %s; using base CV", job.company, added)
        return base_tex, f"base CV (tailored draft added unverified terms: {', '.join(added[:5])})"
    return text, "tailored"
