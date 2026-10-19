from datetime import date

from twoaday.models import Job
from twoaday.score import Scorer

PROFILE = {
    "title_include": ["intern", "graduate"],
    "title_exclude": ["senior", "manager"],
    "locations_allow": ["london", "remote", "lagos"],
    "description_exclude": ["security clearance"],
    "keywords": {"site reliability": 6, "linux": 4, "kubernetes": 4},
}
TODAY = date(2026, 10, 19)


def job(title="SRE Intern", locs=("London",), desc="Linux and Kubernetes", company="Acme", deadline=""):
    return Job("test", company, title, f"https://x/{company}/{title}", list(locs), desc, deadline)


def test_internet_is_not_an_internship():
    ok, why = Scorer(PROFILE, TODAY).eligible(job(title="Engineering Manager, Agentic Internet"))
    assert not ok


def test_senior_titles_are_rejected():
    ok, why = Scorer(PROFILE, TODAY).eligible(job(title="Senior SRE Intern Mentor"))
    assert not ok and "senior" in why


def test_location_must_be_workable():
    ok, why = Scorer(PROFILE, TODAY).eligible(job(locs=("San Francisco, CA",)))
    assert not ok and "location" in why


def test_clearance_rules_it_out():
    ok, _ = Scorer(PROFILE, TODAY).eligible(job(desc="Requires active security clearance"))
    assert not ok


def test_passed_deadline_rules_it_out():
    ok, why = Scorer(PROFILE, TODAY).eligible(job(deadline="2026-10-01"))
    assert not ok and "deadline" in why


def test_title_keywords_count_double():
    s = Scorer(PROFILE, TODAY)
    in_title = s.score(job(title="Site Reliability Intern", desc="")).score
    in_desc = s.score(job(title="Intern", desc="site reliability")).score
    assert in_title > in_desc > 0


def test_pick_skips_seen_and_spreads_companies():
    s = Scorer(PROFILE, TODAY)
    a1 = job(title="Site Reliability Intern", company="A")
    a2 = job(title="Linux Intern", company="A")
    b = job(title="Kubernetes Intern", company="B")
    c = job(title="Linux Graduate", company="C")
    picks = s.pick([a1, a2, b, c], seen={c.key}, n=2)
    assert [p.company for p in picks] == ["A", "B"]
