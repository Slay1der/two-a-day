"""Optional notifications. Each channel turns on only when its secrets are present."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import requests

log = logging.getLogger(__name__)


def format_digest(picks: list[dict], dashboard_url: str = "") -> str:
    if not picks:
        return "Two-a-Day: no new roles passed the filters today. Clear the shortlist instead."
    lines = [f"Two-a-Day: {len(picks)} role(s) for today"]
    for i, p in enumerate(picks, 1):
        due = f" | closes {p['deadline']}" if p.get("deadline") else ""
        lines += [f"\n{i}. {p['company']} | {p['title']}", f"   {p['location_text']}{due}", f"   {p['url']}"]
        if p.get("reasons"):
            lines.append(f"   fit: {', '.join(p['reasons'][:4])}")
    if dashboard_url:
        lines.append(f"\nTracker: {dashboard_url}")
    return "\n".join(lines)


def telegram(text: str, files: list[Path]) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return False
    base = f"https://api.telegram.org/bot{token}"
    requests.post(f"{base}/sendMessage", data={"chat_id": chat, "text": text}, timeout=20).raise_for_status()
    for f in files:
        with f.open("rb") as fh:
            requests.post(
                f"{base}/sendDocument", data={"chat_id": chat}, files={"document": (f.name, fh)}, timeout=60
            ).raise_for_status()
    return True


def email(text: str, files: list[Path]) -> bool:
    user, pw = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    to = os.environ.get("NOTIFY_EMAIL") or user
    if not (user and pw and to):
        return False
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = "Two-a-Day: today's roles", user, to
    msg.set_content(text)
    for f in files:
        msg.add_attachment(f.read_bytes(), maintype="application", subtype="pdf", filename=f.name)
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    with smtplib.SMTP_SSL(host, int(os.environ.get("SMTP_PORT", "465"))) as s:
        s.login(user, pw)
        s.send_message(msg)
    return True


def send(text: str, files: list[Path]) -> list[str]:
    sent = []
    for name, fn in (("telegram", telegram), ("email", email)):
        try:
            if fn(text, files):
                sent.append(name)
        except Exception as e:  # a failed notification must never fail the run
            log.warning("%s notification failed: %s", name, e)
    return sent
