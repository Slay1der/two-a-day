from types import SimpleNamespace

from twoaday.models import Job
from twoaday.tailor import new_facts, tailor

BASE = r"""\documentclass{article}
\begin{document}
\section{Experience}
\resumeItem{Set up Zabbix monitoring and Grafana dashboards for servers}
\resumeItem{Administered Linux servers}
\section{Certifications}
RHCSA, RHCE
\end{document}
"""
JOB = Job("test", "Acme", "SRE Intern", "https://x", ["London"], "Observability, Linux")


class FakeClient:
    def __init__(self, text):
        self.messages = SimpleNamespace(
            create=lambda **_: SimpleNamespace(content=[SimpleNamespace(text=text)])
        )


def test_reordering_is_allowed():
    tailored = BASE.replace(
        r"\resumeItem{Set up Zabbix monitoring and Grafana dashboards for servers}" + "\n"
        r"\resumeItem{Administered Linux servers}",
        r"\resumeItem{Administered Linux servers}" + "\n"
        r"\resumeItem{Set up Zabbix monitoring and Grafana dashboards for servers}",
    )
    assert new_facts(BASE, tailored) == []


def test_invented_metric_and_cert_are_caught():
    bad = BASE.replace("for servers", "for 200 servers").replace("RHCE", "RHCE, CKA")
    added = new_facts(BASE, bad)
    assert "200" in added and "CKA" in added


def test_guard_falls_back_to_base():
    bad = BASE.replace("RHCE", "RHCE, AWS Solutions Architect")
    tex, note = tailor(BASE, JOB, client=FakeClient(bad))
    assert tex == BASE and "unverified" in note


def test_clean_output_is_used_and_fences_stripped():
    good = BASE.replace("Administered Linux servers", "Administered Linux servers in production")
    tex, note = tailor(BASE, JOB, client=FakeClient("```latex\n" + good + "\n```"))
    assert note == "tailored" and tex.startswith(r"\documentclass")


def test_no_key_means_base(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    tex, note = tailor(BASE, JOB)
    assert tex == BASE and "no ANTHROPIC_API_KEY" in note


def test_gemini_is_used_when_only_its_key_is_set(monkeypatch):
    from twoaday import tailor as t

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    client, _ = t.make_client()
    assert isinstance(client, t.GeminiClient)


def test_gemini_request_shape(monkeypatch):
    import requests

    from twoaday.tailor import GeminiClient

    seen = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": BASE}]}}]}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, body=json)
        return Resp()

    monkeypatch.setattr(requests, "post", fake_post)
    tex, note = tailor(BASE, JOB, client=GeminiClient("secret", "gemini-test"), model="gemini-test")
    assert note == "tailored"
    assert seen["url"].endswith("/models/gemini-test:generateContent")
    assert seen["headers"]["x-goog-api-key"] == "secret"
    assert seen["body"]["systemInstruction"]["parts"][0]["text"].startswith("You tailor")


def test_api_failure_falls_back(monkeypatch):
    class Boom:
        messages = SimpleNamespace(create=lambda **_: (_ for _ in ()).throw(RuntimeError("429")))

    tex, note = tailor(BASE, JOB, client=Boom())
    assert tex == BASE and "failed" in note
