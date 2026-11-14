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


def test_shows_config_errors_without_key_or_db(no_dotenv, monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:1/?serverSelectionTimeoutMS=500")
    at = run_app()
    errors = " ".join(e.value for e in at.error)
    assert "GOOGLE_API_KEY" in errors
    assert "Is MongoDB running?" in errors
    assert analyze_button(at).disabled


def test_ready_state_lists_saved_candidates(no_dotenv, monkeypatch, db):
    monkeypatch.setattr(RankResume, "_llm", object())  # pretend Gemini is configured
    db.insert_resume(make_resume())
    db.add_ranking("test_resume_001", RANKING, "Python dev")

    at = run_app()
    assert not at.error
    # Needs a job description and uploaded PDFs before it can run
    assert analyze_button(at).disabled
    assert any("1 candidate(s)" in c.value for c in at.caption)
    assert any("Alice Johnson" in str(o) for o in at.selectbox[-1].options)
