import json
from pathlib import Path

from twoaday.sources import parse_ashby, parse_greenhouse, parse_lever

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text())


def test_greenhouse():
    jobs = parse_greenhouse("acme", load("greenhouse.json"))
    assert len(jobs) == 1
    j = jobs[0]
    assert j.title == "Site Reliability Engineer Intern"
    assert "London, UK" in j.locations
    assert "<p>" not in j.description and "Linux" in j.description
    assert j.deadline == "2026-11-15"


def test_lever_adds_remote():
    jobs = parse_lever("acme", load("lever.json"))
    assert jobs[0].locations == ["Dublin", "Remote"]
    assert jobs[0].url.startswith("https://jobs.lever.co/")


def test_ashby_skips_unlisted():
    jobs = parse_ashby("acme", load("ashby.json"))
    assert [j.title for j in jobs] == ["Infrastructure Intern"]
    assert "Remote" in jobs[0].locations
