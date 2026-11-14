"""Tests for the parse -> store -> rank pipeline.

Gemini is replaced by a scripted fake LLM, so these tests need no API key. The
end-to-end tests use the sample PDFs in the repo and the isolated test database.

    pytest test_pipeline.py
"""
import json
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

import Load_apis
import ResumeAnalyzer
from RankResume import extract_json, normalize_ranking, rank_resume

ROOT = Path(__file__).parent
SAMPLE_PDFS = sorted(ROOT.glob("*.pdf"))

RANKING = {
    "skills": {"score": 35, "justification": "Python"},
    "experience": {"score": 30, "justification": "5y"},
    "projects": {"score": 8, "justification": "ok"},
    "other_relevant_skills": {"score": 7, "justification": "cloud"},
    "extras": {"score": 4, "justification": "cert"},
    "total_score": 84,
}


class FakeLLM:
    """Returns a parsed resume for PDF prompts and a ranking for rank prompts."""

    def __init__(self, parsed, ranking=RANKING, fence=True):
        self.parsed, self.ranking, self.fence = parsed, ranking, fence
        self.calls = []

    def _wrap(self, obj):
        body = json.dumps(obj)
        return AIMessage(content=f"```json\n{body}\n```" if self.fence else body)

    def invoke(self, messages):
        self.calls.append(messages)
        if "ranks resumes" in messages[0].content:
            if isinstance(self.ranking, Exception):
                raise self.ranking
            return self._wrap(self.ranking)
        return self._wrap(self.parsed)


SNAKE_RESUME = {
    "name": "Jane Doe", "contact_information": "+1 555 0100", "email_address": "jane@example.com",
    "linkedin_profile": "linkedin.com/in/jane", "skills": ["Python", "MongoDB"],
    "experience": [{"company": "Acme", "position": "Engineer"}], "education": [{"degree": "BSc"}],
    "projects": [{"name": "HireWise"}], "extras": ["AWS Certified"],
}

# Shape Gemini tends to produce when keys are not pinned down
TITLE_CASE_RESUME = {
    "Name": "John Roe", "Contact Information": "+1 555 0101", "Email": "john@example.com",
    "LinkedIn Profile": "linkedin.com/in/john", "List of Skills": {"languages": ["Python"], "tools": ["Git"]},
    "Work Experience": [{"company": "Initech"}], "Education": "BSc Computer Science",
    "Projects": None, "Extras": [],
}


# --------------------------------------------------------------------------- #
# extract_json
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text", [
    '{"a": 1}',
    '```json\n{"a": 1}\n```',
    '```JSON\n{"a": 1}\n```',
    '```\n{"a": 1}\n```',
    'Here is the result:\n```json\n{"a": 1}\n```\nThanks!',
    'Sure! {"a": 1} hope this helps',
    [{"type": "text", "text": '{"a": 1}'}],
])
def test_extract_json_variants(text):
    assert extract_json(text) == {"a": 1}


def test_extract_json_keeps_word_json_in_values():
    # The old implementation stripped the first "json" substring from the body
    assert extract_json('```\n{"format": "json"}\n```') == {"format": "json"}


def test_extract_json_invalid_raises():
    with pytest.raises(ValueError):
        extract_json("no json here")


# --------------------------------------------------------------------------- #
# normalize_ranking
# --------------------------------------------------------------------------- #
def test_normalize_ranking_recomputes_total():
    wrong_total = {**RANKING, "total_score": 12}
    assert normalize_ranking(wrong_total)["total_score"] == 84


def test_normalize_ranking_clamps_and_fills_missing():
    ranking = normalize_ranking({
        "skills": {"score": 55, "justification": "too high"},
        "experience": {"score": -3},
        "projects": "7",
    })
    assert ranking["skills"]["score"] == 40
    assert ranking["experience"]["score"] == 0
    assert ranking["projects"]["score"] == 7
    assert ranking["other_relevant_skills"] == {"score": 0, "justification": ""}
    assert ranking["total_score"] == 47


def test_rank_resume_rejects_empty_jd():
    with pytest.raises(ValueError):
        rank_resume(SNAKE_RESUME, "   ", llm=FakeLLM(SNAKE_RESUME))


def test_rank_resume_hides_internal_fields():
    llm = FakeLLM(SNAKE_RESUME)
    rank_resume({**SNAKE_RESUME, "_id": "secret-id", "rankings": []}, "Python dev", llm=llm)
    prompt = llm.calls[0][1].content
    assert "secret-id" not in prompt and "Python dev" in prompt


# --------------------------------------------------------------------------- #
# normalize_resume / parse_resume
# --------------------------------------------------------------------------- #
def test_normalize_resume_title_case_keys():
    resume = ResumeAnalyzer.normalize_resume(TITLE_CASE_RESUME)
    assert resume["name"] == "John Roe"
    assert resume["email_address"] == "john@example.com"
    assert resume["skills"] == ["Python", "Git"]
    assert resume["experience"] == [{"company": "Initech"}]
    assert resume["education"] == ["BSc Computer Science"]
    assert resume["projects"] == []


def test_normalize_resume_unwraps_and_fills_defaults():
    resume = ResumeAnalyzer.normalize_resume({"resume": {"name": "X"}})
    assert resume["name"] == "X"
    assert resume["linkedin_profile"] is None
    assert all(resume[f] == [] for f in ResumeAnalyzer.LIST_FIELDS)


@pytest.mark.skipif(not SAMPLE_PDFS, reason="no sample PDFs")
def test_parse_resume_sends_pdf():
    llm = FakeLLM(SNAKE_RESUME, fence=False)
    pdf = ResumeAnalyzer.load_pdf_as_gemini_file(SAMPLE_PDFS[0])
    assert ResumeAnalyzer.parse_resume(pdf, llm=llm)["name"] == "Jane Doe"
    part = llm.calls[0][1].content[0]
    assert part["type"] == "media" and part["mime_type"] == "application/pdf"


def test_load_pdf_rejects_non_pdf(tmp_path):
    bad = tmp_path / "fake.pdf"
    bad.write_text("not a pdf")
    with pytest.raises(ValueError):
        ResumeAnalyzer.load_pdf_as_gemini_file(bad)


def test_collect_pdf_paths(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "b.PDF").write_bytes(b"%PDF-1.4")
    (tmp_path / "notes.txt").write_text("x")
    found = ResumeAnalyzer.collect_pdf_paths([str(tmp_path), str(tmp_path / "a.pdf")])
    assert [p.name for p in found] == ["a.pdf", "b.PDF"]


# --------------------------------------------------------------------------- #
# Load_apis
# --------------------------------------------------------------------------- #
def test_load_apis_missing_key_gives_clear_error(monkeypatch):
    monkeypatch.setattr(Load_apis, "load_dotenv", lambda: None)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        Load_apis.load_apis()


def test_main_without_api_key_exits_cleanly(monkeypatch, capsys):
    monkeypatch.setattr(Load_apis, "load_dotenv", lambda: None)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr("RankResume._llm", None)
    code = ResumeAnalyzer.main([str(ROOT), "-j", "Python dev"])
    assert code == 2
    assert "GOOGLE_API_KEY" in capsys.readouterr().out


def test_main_rejects_empty_job_description(capsys):
    assert ResumeAnalyzer.main([str(ROOT), "-j", "  "], llm=FakeLLM(SNAKE_RESUME)) == 2


# --------------------------------------------------------------------------- #
# End to end (sample PDFs -> fake Gemini -> MongoDB)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(len(SAMPLE_PDFS) < 2, reason="needs the sample PDFs")
@pytest.mark.parametrize("parsed", [SNAKE_RESUME, TITLE_CASE_RESUME], ids=["snake_keys", "title_keys"])
def test_end_to_end(db, parsed, capsys):
    code = ResumeAnalyzer.main([str(p) for p in SAMPLE_PDFS] + ["-j", "Senior Python developer"],
                               llm=FakeLLM(parsed))
    out = capsys.readouterr().out
    assert code == 0, out
    assert "LEADERBOARD" in out

    docs = db.get_all_resumes()
    assert len(docs) == len(SAMPLE_PDFS)
    for doc in docs:
        assert isinstance(doc["skills"], list), "ranking must not overwrite resume fields"
        assert doc["total_score"] == 84
        assert doc["latest_ranking"]["job_description"] == "Senior Python developer"
        assert len(doc["rankings"]) == 1
        assert doc["source_file"] in {p.name for p in SAMPLE_PDFS}
    # skills stay searchable after ranking
    assert db.get_resume_count({"skills": {"$in": ["Python"]}}) == len(SAMPLE_PDFS)


@pytest.mark.skipif(not SAMPLE_PDFS, reason="needs the sample PDFs")
def test_end_to_end_ranking_failure_keeps_going(db, capsys):
    llm = FakeLLM(SNAKE_RESUME, ranking=RuntimeError("quota exceeded"))
    code = ResumeAnalyzer.main([str(SAMPLE_PDFS[0]), "-j", "Python dev"], llm=llm)
    out = capsys.readouterr().out
    assert code == 1
    assert "quota exceeded" in out
    doc = db.get_all_resumes()[0]
    assert doc["name"] == "Jane Doe" and "total_score" not in doc


def test_end_to_end_bad_file_is_reported(db, tmp_path, capsys):
    good = SAMPLE_PDFS[0]
    missing = tmp_path / "missing.pdf"
    code = ResumeAnalyzer.main([str(good), str(missing), "-j", "Python dev"], llm=FakeLLM(SNAKE_RESUME))
    out = capsys.readouterr().out
    assert code == 1
    assert "missing.pdf" in out
    assert db.get_resume_count() == 1


def test_jd_file_option(db, tmp_path, capsys):
    jd = tmp_path / "jd.txt"
    jd.write_text("  Backend engineer, Python  \n")
    assert ResumeAnalyzer.main([str(SAMPLE_PDFS[0]), "--jd-file", str(jd)], llm=FakeLLM(SNAKE_RESUME)) == 0
    assert db.get_all_resumes()[0]["latest_ranking"]["job_description"] == "Backend engineer, Python"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
