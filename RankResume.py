import json
import re
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from Load_apis import load_apis, load_llm

# Category -> maximum score. These must add up to 100.
SCORE_WEIGHTS = {
    "skills": 40,
    "experience": 35,
    "projects": 10,
    "other_relevant_skills": 10,
    "extras": 5,
}

# Fields added by the database layer that the LLM should never see.
_INTERNAL_FIELDS = {"_id", "created_at", "updated_at", "rankings", "latest_ranking", "total_score"}

_llm = None


def get_llm():
    """Create the LLM lazily so importing this module has no side effects."""
    global _llm
    if _llm is None:
        load_apis()
        _llm = load_llm()
    return _llm


def _response_text(content: Any) -> str:
    """Normalise an LLM message content (str or list of content blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content)


def extract_json(text: Any) -> Dict[str, Any]:
    """Extract the first JSON object from an LLM response.

    Handles plain JSON, ```json fenced blocks, and JSON surrounded by prose.

    Raises:
        ValueError: if no valid JSON object can be found.
    """
    text = _response_text(text).strip()

    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response: {text[:200]!r}")


def _to_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_ranking(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an LLM ranking: clamp each score to its range and recompute the total.

    LLMs regularly mis-add, exceed category maximums, or omit a category, so the
    total is always derived here rather than trusted from the model.
    """
    if not isinstance(raw, dict):
        raise ValueError("Ranking must be a JSON object")

    ranking: Dict[str, Any] = {}
    total = 0.0
    for category, max_score in SCORE_WEIGHTS.items():
        entry = raw.get(category)
        if isinstance(entry, dict):
            score = _to_number(entry.get("score"))
            justification = str(entry.get("justification", "")).strip()
        else:
            score = _to_number(entry)
            justification = ""
        score = max(0.0, min(float(max_score), score))
        score = int(score) if score.is_integer() else round(score, 1)
        ranking[category] = {"score": score, "justification": justification}
        total += score

    ranking["total_score"] = int(total) if float(total).is_integer() else round(total, 1)
    return ranking


def _resume_for_prompt(resume: Dict[str, Any]) -> str:
    clean = {k: v for k, v in resume.items() if k not in _INTERNAL_FIELDS}
    return json.dumps(clean, indent=2, default=str)


def rank_resume(resume: dict, user_input: str, llm=None) -> Dict[str, Any]:
    """Score a parsed resume against a job description (0-100)."""
    if not user_input or not user_input.strip():
        raise ValueError("Job description cannot be empty")

    llm = llm or get_llm()
    system_message = SystemMessage(content="""You are a helpful assistant that ranks resumes based on a Job Description. You must follow the following criteria to rank the resume, and every score must reflect relevance to the Job Description.

    Analyze the resume and provide scores for each category. Return ONLY a valid JSON object with the following structure:
    {
        "skills": {
            "score": <number out of 40>,
            "justification": "<brief explanation>"
        },
        "experience": {
            "score": <number out of 35>,
            "justification": "<brief explanation>"
        },
        "projects": {
            "score": <number out of 10>,
            "justification": "<brief explanation>"
        },
        "other_relevant_skills": {
            "score": <number out of 10>,
            "justification": "<brief explanation>"
        },
        "extras": {
            "score": <number out of 5>,
            "justification": "<brief explanation>"
        },
        "total_score": <sum of all scores out of 100>
    }

    Return ONLY the JSON object, no additional text or formatting.""")
    human_message = HumanMessage(
        content=(
            f"Resume (JSON):\n{_resume_for_prompt(resume)}\n\n"
            f"Job Description:\n{user_input.strip()}"
        )
    )
    response = llm.invoke([system_message, human_message])
    return normalize_ranking(extract_json(response.content))
