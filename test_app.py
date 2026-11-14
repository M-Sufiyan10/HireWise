"""Smoke tests for the Streamlit UI (app.py) using Streamlit's headless AppTest."""
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

import Db  # noqa: E402
import Load_apis  # noqa: E402
import RankResume  # noqa: E402
from test_db import RANKING, make_resume  # noqa: E402


@pytest.fixture
def no_dotenv(monkeypatch):
    """Stop .env from overriding the environment set up by each test."""
    monkeypatch.setattr(Load_apis, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(Db, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(RankResume, "_llm", None)


def run_app():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def analyze_button(at):
    return next(b for b in at.button if b.label == "Analyze & rank")


BACKEND_TERMS = ("mongo", "gemini", "google_api_key", "api key", "database", "model", "connected")


def page_text(at) -> str:
    """The app's own UI text (titles, alerts, buttons), lower-cased.

    Markdown and captions are excluded because they render candidate content
    (skills, score justifications) that may legitimately mention "MongoDB".
    """
    parts = []
    for kind in ("title", "header", "subheader", "error",
                 "warning", "info", "success", "text"):
        parts += [str(el.value) for el in getattr(at, kind)]
    parts += [b.label for b in at.button]
    return " ".join(parts).lower()


def test_unavailable_backend_shows_generic_message(no_dotenv, monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:1/?serverSelectionTimeoutMS=500")
    at = run_app()
    assert any("temporarily unavailable" in e.value for e in at.error)
    text = page_text(at)
    assert not [t for t in BACKEND_TERMS if t in text], text
    assert not any(b.label == "Analyze & rank" for b in at.button)  # nothing usable is shown
    assert any(b.label == "Try again" for b in at.button)


def test_ready_state_lists_saved_candidates(no_dotenv, monkeypatch, db):
    monkeypatch.setattr(RankResume, "_llm", object())  # pretend Gemini is configured
    db.insert_resume(make_resume())
    db.add_ranking("test_resume_001", RANKING, "Python dev")

    at = run_app()
    assert not at.error
    text = page_text(at)
    assert not [t for t in BACKEND_TERMS if t in text], text
    # Needs a job description and uploaded PDFs before it can run
    assert analyze_button(at).disabled
    assert any("1 candidate(s)" in c.value for c in at.caption)
    assert any("Alice Johnson" in str(o) for o in at.selectbox[-1].options)
