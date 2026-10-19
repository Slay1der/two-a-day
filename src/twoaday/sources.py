from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

import requests

from .models import Job, strip_html

log = logging.getLogger(__name__)
TIMEOUT = 20
HEADERS = {"User-Agent": "two-a-day/0.1 (personal job search; github.com/Slay1der)"}


def _get_json(url: str, session: requests.Session):
    resp = session.get(url, timeout=TIMEOUT, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def parse_greenhouse(board: str, payload: dict) -> list[Job]:
    jobs = []
    for j in payload.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        offices = [o.get("name", "") for o in j.get("offices", []) if o.get("name")]
        jobs.append(
            Job(
                source="greenhouse",
                company=j.get("company_name") or board,
                title=j.get("title", "").strip(),
                url=j.get("absolute_url", ""),
                locations=[loc, *[o for o in offices if o.lower() not in loc.lower()]] if loc else offices,
                description=strip_html(j.get("content", "")),
                deadline=(j.get("application_deadline") or "")[:10],
                posted=(j.get("first_published") or j.get("updated_at") or "")[:10],
            )
        )
    return jobs


def parse_lever(company: str, payload: list) -> list[Job]:
    jobs = []
    for j in payload:
        cats = j.get("categories") or {}
        locs = cats.get("allLocations") or ([cats["location"]] if cats.get("location") else [])
        if j.get("workplaceType") == "remote":
            locs = [*locs, "Remote"]
        jobs.append(
            Job(
                source="lever",
                company=company.title(),
                title=j.get("text", "").strip(),
                url=j.get("hostedUrl", ""),
                locations=locs,
                description=j.get("descriptionPlain") or strip_html(j.get("description", "")),
            )
        )
    return jobs


def parse_ashby(board: str, payload: dict) -> list[Job]:
    jobs = []
    for j in payload.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        if j.get("isRemote"):
            locs.append("Remote")
        jobs.append(
            Job(
                source="ashby",
                company=board.title(),
                title=j.get("title", "").strip(),
                url=j.get("jobUrl", ""),
                locations=[x for x in locs if x],
                description=j.get("descriptionPlain") or strip_html(j.get("descriptionHtml", "")),
                posted=(j.get("publishedAt") or "")[:10],
            )
        )
    return jobs


FETCHERS: dict[str, tuple[str, Callable]] = {
    "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/{name}/jobs?content=true", parse_greenhouse),
    "lever": ("https://api.lever.co/v0/postings/{name}?mode=json", parse_lever),
    "ashby": ("https://api.ashbyhq.com/posting-api/job-board/{name}", parse_ashby),
}


def fetch_all(sources: dict[str, Iterable[str]], session: requests.Session | None = None) -> list[Job]:
    session = session or requests.Session()
    found: list[Job] = []
    for kind, names in (sources or {}).items():
        if kind not in FETCHERS:
            log.warning("unknown source type %r, skipping", kind)
            continue
        template, parser = FETCHERS[kind]
        for name in names or []:
            try:
                jobs = parser(name, _get_json(template.format(name=name), session))
                log.info("%s/%s: %d postings", kind, name, len(jobs))
                found.extend(jobs)
            except requests.HTTPError as e:
                log.warning("%s/%s: HTTP %s, skipping", kind, name, e.response.status_code)
            except (requests.RequestException, ValueError) as e:
                log.warning("%s/%s: %s, skipping", kind, name, e)
    return found
