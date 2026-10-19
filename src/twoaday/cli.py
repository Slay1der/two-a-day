from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

import yaml

from . import latex, notify, site, sources
from .score import Scorer
from .store import STATUSES, Store
from .tailor import tailor

log = logging.getLogger("twoaday")

PLACEHOLDER_PHONE = "+234 000 000 0000"
PLACEHOLDER_EMAIL = "you@example.com"


def with_contact(tex: str) -> str:
    """Swap the placeholder phone and email in the committed CV for the real ones from secrets."""
    phone, email = os.environ.get("CV_PHONE", "").strip(), os.environ.get("CV_EMAIL", "").strip()
    if phone:
        digits = "+" + "".join(c for c in phone if c.isdigit())
        tex = tex.replace("tel:+2340000000000", "tel:" + digits).replace(PLACEHOLDER_PHONE, phone)
    if email:
        tex = tex.replace(PLACEHOLDER_EMAIL, email)
    return tex


def run(root: Path, picks: int | None, dry_run: bool, no_pdf: bool) -> int:
    profile = yaml.safe_load((root / "config" / "profile.yaml").read_text(encoding="utf-8"))
    store = Store(root)
    n = picks or int(profile.get("picks_per_day", 2))

    jobs = sources.fetch_all(profile.get("sources", {}))
    log.info("fetched %d postings", len(jobs))
    chosen = Scorer(profile).pick(jobs, store.seen() | {a.get("key") for a in store.apps()}, n)
    log.info("picked %d", len(chosen))

    base_tex = with_contact((root / "cv" / "base.tex").read_text(encoding="utf-8"))
    today = date.today().isoformat()
    entries, pdfs = [], []
    for job in chosen:
        entry = job.to_dict()
        entry["location_text"] = job.location_text
        if dry_run:
            print(f"- {job.company} | {job.title} | {job.location_text} | score {job.score} | {job.url}")
            entries.append(entry)
            continue
        tex, note = tailor(base_tex, job)
        entry["cv_note"] = note
        if not no_pdf:
            name = f"{today}_{latex.slug(job.company, 20)}_{latex.slug(job.title)}.pdf"
            try:
                pdf = latex.compile_pdf(tex, root / "docs" / "cvs" / name)
                if latex.page_count(pdf) > 1:
                    log.warning("%s runs over one page; sending base CV instead", name)
                    pdf = latex.compile_pdf(base_tex, pdf)
                    entry["cv_note"] = "base CV (tailored version ran over one page)"
                entry["cv"] = name
                pdfs.append(pdf)
            except RuntimeError as e:
                log.error("could not build CV for %s: %s", job.company, e)
        store.add(entry)
        entries.append(entry)

    if dry_run:
        return 0
    store.mark_seen(j.key for j in chosen)
    site.write(store.apps(), root / "docs")
    sent = notify.send(notify.format_digest(entries, os.environ.get("DASHBOARD_URL", "")), pdfs)
    log.info("notified via %s", ", ".join(sent) or "nothing (no channel configured)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="twoaday", description="Two quality job applications a day.")
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="find today's roles, tailor CVs, update the dashboard, notify")
    r.add_argument("--picks", type=int)
    r.add_argument("--dry-run", action="store_true", help="print the picks only; change nothing")
    r.add_argument("--no-pdf", action="store_true", help="skip LaTeX compilation")

    s = sub.add_parser("status", help="update an application's status")
    s.add_argument("key", help="application key (first 8 characters are enough)")
    s.add_argument("status", choices=STATUSES)

    sub.add_parser("site", help="rebuild docs/index.html from data/apps.json")
    sub.add_parser("list", help="print every application")

    args = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s"
    )
    store = Store(args.root)

    if args.cmd == "run":
        return run(args.root, args.picks, args.dry_run, args.no_pdf)
    if args.cmd == "status":
        a = store.set_status(args.key, args.status)
        site.write(store.apps(), args.root / "docs")
        print(f"{a['company']} | {a['title']} -> {a['status']}")
        return 0
    if args.cmd == "site":
        print(site.write(store.apps(), args.root / "docs"))
        return 0
    if args.cmd == "list":
        for a in store.apps():
            print(
                f"{a.get('key', '')[:8]}  {a.get('status', ''):<11} {a.get('company', '')} | {a.get('title', '')}"
            )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
