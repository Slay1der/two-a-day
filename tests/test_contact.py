from twoaday.cli import with_contact

TEX = r"\href{tel:+2340000000000}{+234 000 000 0000} \href{mailto:you@example.com}{you@example.com}"


def test_placeholders_swapped(monkeypatch):
    monkeypatch.setenv("CV_PHONE", "+234 801 234 5678")
    monkeypatch.setenv("CV_EMAIL", "me@mail.com")
    out = with_contact(TEX)
    assert "tel:+2348012345678" in out and "+234 801 234 5678" in out
    assert "me@mail.com" in out and "example.com" not in out


def test_no_secrets_keeps_placeholders(monkeypatch):
    monkeypatch.delenv("CV_PHONE", raising=False)
    monkeypatch.delenv("CV_EMAIL", raising=False)
    assert with_contact(TEX) == TEX
