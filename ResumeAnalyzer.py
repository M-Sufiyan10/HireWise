"""HireWise resume pipeline.

Parses resume PDFs with Gemini, stores them in MongoDB, ranks each one against
a job description and prints a leaderboard.

Usage:
    python ResumeAnalyzer.py [PDF_OR_DIR ...] [--job-description TEXT | --jd-file PATH]

With no paths, every PDF in the current directory is processed. With no job
description option, you are prompted for one.
"""
import argparse
import base64
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from Db import ResumeDatabase
from RankResume import extract_json, get_llm, rank_resume

LIST_FIELDS = ("skills", "experience", "education", "projects", "extras")
CONTACT_FIELDS = ("name", "contact_information", "email_address", "linkedin_profile")
RESUME_FIELDS = CONTACT_FIELDS + LIST_FIELDS

# LLMs don't always use the exact key names asked for; map common variants.
_KEY_ALIASES = {
    "full_name": "name",
    "candidate_name": "name",
    "contact": "contact_information",
    "contact_info": "contact_information",
    "contact_details": "contact_information",
    "phone": "contact_information",
    "phone_number": "contact_information",
    "email": "email_address",
    "email_id": "email_address",
    "linkedin": "linkedin_profile",
    "linkedin_url": "linkedin_profile",
    "list_of_skills": "skills",
    "technical_skills": "skills",
    "list_of_experience": "experience",
    "work_experience": "experience",
    "professional_experience": "experience",
    "experiences": "experience",
    "list_of_education": "education",
    "list_of_projects": "projects",
    "project": "projects",
    "list_of_extras": "extras",
    "extra": "extras",
}

PARSE_PROMPT = """You are a helpful assistant. Analyze this resume PDF and extract the candidate's information.

Return ONLY a valid JSON object with exactly these keys:
{
    "name": "<full name>",
    "contact_information": "<phone number and/or address>",
    "email_address": "<email>",
    "linkedin_profile": "<LinkedIn URL>",
    "skills": ["<skill>", ...],
    "experience": [{"company": "...", "position": "...", "duration": "...", "description": "..."}, ...],
    "education": [{"degree": "...", "institution": "...", "year": "..."}, ...],
    "projects": [{"name": "...", "description": "...", "technologies": ["..."]}, ...],
    "extras": ["<certifications, awards, publications, patents, interests, courses, etc.>", ...]
}

Use null for missing single values and [] for missing lists. Return ONLY the JSON object, no additional text or formatting."""


class InvalidPDFError(ValueError):
    """Raised when an uploaded/loaded file is not a PDF."""


def pdf_bytes_to_gemini_file(pdf_bytes: bytes, name: str = "file") -> Dict[str, str]:
    if not pdf_bytes.startswith(b"%PDF"):
        raise InvalidPDFError(f"{name} is not a valid PDF file")
    return {
        "mime_type": "application/pdf",
        "data": base64.b64encode(pdf_bytes).decode()
    }


def load_pdf_as_gemini_file(path) -> Dict[str, str]:
    with open(path, "rb") as f:
        return pdf_bytes_to_gemini_file(f.read(), str(path))


def _canonical_key(key: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")
    return _KEY_ALIASES.get(key, key)


def normalize_resume(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce an LLM-parsed resume into the canonical schema.

    Keys are lower/snake-cased and aliased (e.g. "Email" -> "email_address"),
    list fields are guaranteed to be lists, and unknown keys are preserved.
    """
    if not isinstance(raw, dict):
        raise ValueError("Parsed resume must be a JSON object")

    # Some models wrap everything in a top-level key such as {"resume": {...}}
    if len(raw) == 1:
        only = next(iter(raw.values()))
        if isinstance(only, dict) and not any(_canonical_key(k) in RESUME_FIELDS for k in raw):
            raw = only

    resume: Dict[str, Any] = {}
    for key, value in raw.items():
        canonical = _canonical_key(key)
        if canonical in resume and not resume[canonical]:
            resume[canonical] = value
        elif canonical not in resume:
            resume[canonical] = value

    for field in CONTACT_FIELDS:
        resume.setdefault(field, None)

    for field in LIST_FIELDS:
        value = resume.get(field)
        if value is None or value == "":
            resume[field] = []
        elif isinstance(value, dict):
            # e.g. {"languages": [...], "frameworks": [...]} -> flat list
            if all(isinstance(v, list) for v in value.values()):
                resume[field] = [item for v in value.values() for item in v]
            else:
                resume[field] = [value]
        elif not isinstance(value, list):
            resume[field] = [value]

    return resume


def parse_resume(pdf_file: dict, llm=None) -> Dict[str, Any]:
    llm = llm or get_llm()
    system_msg = SystemMessage(content=PARSE_PROMPT)
    human_msg = HumanMessage(
        content=[
            {
                "type": "media",
                "mime_type": pdf_file["mime_type"],
                "data": pdf_file["data"]
            }
        ]
    )
    response = llm.invoke([system_msg, human_msg])
    return normalize_resume(extract_json(response.content))


def collect_pdf_paths(inputs: List[str]) -> List[Path]:
    """Expand files/directories into a sorted, de-duplicated list of PDFs."""
    if not inputs:
        inputs = ["."]
    paths: List[Path] = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            paths.extend(sorted(x for x in p.iterdir() if x.is_file() and x.suffix.lower() == ".pdf"))
        else:
            paths.append(p)
    seen, unique = set(), []
    for p in paths:
        key = p.resolve()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def process_resume_bytes(pdf_bytes: bytes, filename: str, job_description: str,
                         db: ResumeDatabase, llm=None, verbose: bool = True) -> Dict[str, Any]:
    """Parse, store and rank a single resume given its PDF bytes.

    Returns a summary with the file name, stored id, candidate name, total score,
    full ranking breakdown, parsed resume and any ranking error.
    """
    log = print if verbose else (lambda *a, **k: None)
    resume = parse_resume(pdf_bytes_to_gemini_file(pdf_bytes, filename), llm=llm)
    resume["source_file"] = filename

    result = db.insert_resume(resume)
    resume_id = result["id"]
    name = resume.get("name") or "Unknown"
    log(f"✓ Resume inserted: {name} (ID: {resume_id})")

    summary = {"file": filename, "id": resume_id, "name": name, "total_score": None,
               "ranking": None, "resume": resume, "error": None}
    try:
        ranking = rank_resume(resume, job_description, llm=llm)
    except Exception as e:  # keep the parsed resume, but report the failure
        summary["error"] = f"ranking failed: {e}"
        log(f"✗ Error ranking resume: {e}")
        return summary

    db.add_ranking(resume_id, ranking, job_description)
    summary["total_score"] = ranking["total_score"]
    summary["ranking"] = ranking
    log(f"✓ Total score: {ranking['total_score']} / 100")
    return summary


def process_resume(path, job_description: str, db: ResumeDatabase, llm=None) -> Dict[str, Any]:
    """Parse, store and rank a single resume file. Returns a result summary."""
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    return process_resume_bytes(pdf_bytes, Path(path).name, job_description, db, llm=llm)


def print_leaderboard(results: List[Dict[str, Any]]):
    ranked = sorted(
        (r for r in results if r["total_score"] is not None),
        key=lambda r: r["total_score"], reverse=True,
    )
    failed = [r for r in results if r["total_score"] is None]

    print(f"\n{'=' * 60}\nLEADERBOARD\n{'=' * 60}")
    if not ranked:
        print("No resumes were ranked.")
    for i, r in enumerate(ranked, 1):
        print(f"{i:>2}. {r['total_score']:>5} / 100  {r['name']}  ({r['file']})")
    for r in failed:
        print(f"  ✗ {r['file']}: {r['error']}")


def read_job_description(args) -> str:
    if args.jd_file:
        return Path(args.jd_file).read_text(encoding="utf-8").strip()
    if args.job_description:
        return args.job_description.strip()
    print("-" * 100)
    jd = input("Enter the Job Description: ").strip()
    print("-" * 100)
    return jd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse and rank resumes against a job description.")
    parser.add_argument("paths", nargs="*", help="Resume PDFs or directories of PDFs (default: current directory)")
    jd = parser.add_mutually_exclusive_group()
    jd.add_argument("-j", "--job-description", help="Job description text")
    jd.add_argument("--jd-file", help="Path to a text file containing the job description")
    return parser


def main(argv: Optional[List[str]] = None, llm=None) -> int:
    args = build_parser().parse_args(argv)
    start_time = time.time()

    # Validate configuration and inputs before asking for anything interactively
    try:
        llm = llm or get_llm()
    except RuntimeError as e:
        print(f"✗ {e}")
        return 2

    files = collect_pdf_paths(args.paths)
    if not files:
        print("✗ No PDF files found to process")
        return 2

    try:
        job_description = read_job_description(args)
    except (OSError, EOFError) as e:
        print(f"✗ Could not read job description: {e}")
        return 2
    if not job_description:
        print("✗ Job description cannot be empty")
        return 2

    results: List[Dict[str, Any]] = []
    try:
        with ResumeDatabase() as db:
            for file in files:
                print(f"\nProcessing: {file}")
                print("-" * 50)
                try:
                    results.append(process_resume(file, job_description, db, llm=llm))
                except Exception as e:
                    print(f"✗ Error processing {file}: {e}")
                    results.append({"file": Path(file).name, "id": None, "name": None,
                                    "total_score": None, "error": str(e)})
                print("-" * 50)
    except KeyboardInterrupt:
        print("\n✗ Interrupted")
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        return 1

    print_leaderboard(results)
    print(f"\nTime taken: {time.time() - start_time:.2f} seconds")
    return 0 if results and all(r["error"] is None for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
