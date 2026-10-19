"""Renders docs/index.html (served by GitHub Pages) from data/apps.json."""

from __future__ import annotations

import html
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

SENT = {"Applied", "Assessment", "Interview", "Offer", "Rejected", "Withdrawn"}
LIVE = {"Applied", "Assessment", "Interview", "Offer"}


def stats(apps: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    per_day = Counter(a["applied"] for a in apps if a.get("applied") and a.get("status") in SENT)
    week = sum(per_day.get((today - timedelta(days=i)).isoformat(), 0) for i in range(7))
    streak, i = 0, 0 if per_day.get(today.isoformat(), 0) >= 2 else 1
    while per_day.get((today - timedelta(days=i)).isoformat(), 0) >= 2:
        streak, i = streak + 1, i + 1
    return {
        "today": per_day.get(today.isoformat(), 0),
        "week": week,
        "streak": streak,
        "live": sum(1 for a in apps if a.get("status") in LIVE),
    }


def _row(a: dict, date_field: str) -> str:
    e = html.escape
    title = f'<a href="{e(a.get("url", ""))}">{e(a.get("title", ""))}</a>' if a.get("url") else e(a["title"])
    cv = f' · <a href="cvs/{e(a["cv"])}">CV</a>' if a.get("cv") else ""
    return (
        f"<tr><td><b>{title}</b><div class=m>{e(a.get('company', ''))}{cv}</div></td>"
        f"<td>{e(a.get('location_text', ''))}</td><td class=n>{e(a.get(date_field) or '—')}</td>"
        f"<td><span class='s s-{e(a.get('status', ''))}'>{e(a.get('status', ''))}</span></td>"
        f"<td class=n>{e(a.get('key', '')[:8])}</td></tr>"
    )


def render(apps: list[dict], today: date | None = None) -> str:
    s = stats(apps, today)
    queue = sorted(
        (a for a in apps if a.get("status") not in SENT), key=lambda a: a.get("deadline") or "9999"
    )
    pipe = sorted(
        (a for a in apps if a.get("status") in SENT), key=lambda a: a.get("applied", ""), reverse=True
    )
    q = "".join(_row(a, "deadline") for a in queue) or "<tr><td colspan=5>Nothing queued.</td></tr>"
    p = "".join(_row(a, "applied") for a in pipe) or "<tr><td colspan=5>Nothing sent yet.</td></tr>"
    return f"""<!doctype html><html lang=en><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Two-a-Day</title>
<style>
:root{{--bg:#f5f6f4;--fg:#17201d;--mu:#5d6a65;--ln:#dfe4e1;--ac:#1f6f5c;--card:#fff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111614;--fg:#e6ece9;--mu:#97a59f;--ln:#2a3531;--ac:#5cc4a6;--card:#18201d}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0}}
main{{max-width:960px;margin:auto;padding:24px 16px;display:grid;gap:24px}}
.k{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.k div{{background:var(--card);border:1px solid var(--ln);border-radius:10px;padding:12px 14px}}
.k b{{display:block;font:600 1.8rem ui-monospace,monospace}}.k span,.m{{color:var(--mu);font-size:.85rem}}
.t{{overflow-x:auto;background:var(--card);border:1px solid var(--ln);border-radius:10px}}
table{{width:100%;border-collapse:collapse;min-width:620px}}td,th{{padding:9px 12px;border-bottom:1px solid var(--ln);text-align:left}}
th,h2{{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;color:var(--mu)}}a{{color:var(--fg)}}
.n{{font-family:ui-monospace,monospace;font-size:.85rem}}.s{{border-radius:99px;padding:2px 9px;font-size:.8rem;border:1px solid var(--ln)}}
.s-Applied,.s-Assessment,.s-Interview{{color:var(--ac);border-color:var(--ac)}}.s-Offer{{background:var(--ac);color:var(--bg)}}
</style><main><h1>Two-a-Day</h1>
<section class=k><div><span>Applied today</span><b>{s["today"]}/2</b></div><div><span>Last 7 days</span><b>{s["week"]}/14</b></div>
<div><span>Streak (days at 2+)</span><b>{s["streak"]}</b></div><div><span>In play</span><b>{s["live"]}</b></div></section>
<section><h2>Shortlist</h2><div class=t><table><tr><th>Role</th><th>Location</th><th>Deadline</th><th>Status</th><th>Key</th></tr>{q}</table></div></section>
<section><h2>Pipeline</h2><div class=t><table><tr><th>Role</th><th>Location</th><th>Applied</th><th>Status</th><th>Key</th></tr>{p}</table></div></section>
<p class=m>Update a status: Actions → "Update status" → enter the key. Generated {html.escape((today or date.today()).isoformat())}.</p>
</main></html>
"""


def write(apps: list[dict], out_dir: Path, today: date | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "index.html"
    path.write_text(render(apps, today), encoding="utf-8")
    return path
