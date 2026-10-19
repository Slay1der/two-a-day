from datetime import date

import pytest

from twoaday import site
from twoaday.store import Store


def test_add_is_idempotent_and_status_sets_applied(tmp_path):
    s = Store(tmp_path)
    s.add({"key": "abc12345ff", "company": "Acme", "title": "SRE Intern"})
    s.add({"key": "abc12345ff", "company": "Acme", "title": "SRE Intern"})
    assert len(s.apps()) == 1
    a = s.set_status("abc12345", "Applied", on=date(2026, 10, 19))
    assert a["applied"] == "2026-10-19"
    with pytest.raises(ValueError):
        s.set_status("abc12345", "Ghosted")


def test_stats_streak():
    apps = [
        {"status": "Applied", "applied": "2026-10-19"},
        {"status": "Applied", "applied": "2026-10-19"},
        {"status": "Interview", "applied": "2026-10-18"},
        {"status": "Applied", "applied": "2026-10-18"},
        {"status": "Applied", "applied": "2026-10-16"},
        {"status": "Shortlisted", "applied": ""},
    ]
    st = site.stats(apps, date(2026, 10, 19))
    assert st == {"today": 2, "week": 5, "streak": 2, "live": 5}


def test_render_escapes(tmp_path):
    out = site.write(
        [{"title": "<script>", "company": "A", "status": "Shortlisted"}], tmp_path, date(2026, 10, 19)
    )
    assert "<script>" not in out.read_text().split("<main>")[1]
