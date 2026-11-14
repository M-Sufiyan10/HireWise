"""HireWise web UI.

Run with:
    streamlit run app.py
"""
import os
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from pymongo.errors import ServerSelectionTimeoutError

from Db import ResumeDatabase
from Load_apis import DEFAULT_MODEL
from RankResume import SCORE_WEIGHTS, get_llm
from ResumeAnalyzer import process_resume_bytes

st.set_page_config(page_title="HireWise", page_icon="🧭", layout="wide")

CATEGORY_LABELS = {
    "skills": "Skills",
    "experience": "Experience",
    "projects": "Projects",
    "other_relevant_skills": "Other relevant skills",
    "extras": "Extras",
}


# --------------------------------------------------------------------------- #
# Resources
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def get_db() -> ResumeDatabase:
    return ResumeDatabase()


def connect_db() -> tuple[Optional[ResumeDatabase], Optional[str]]:
    try:
        return get_db(), None
    except ServerSelectionTimeoutError:
        return None, "can't reach the server at MONGO_URI. Is MongoDB running?"
    except Exception as e:
        return None, str(e).split(",")[0]


def connect_llm() -> tuple[Any, Optional[str]]:
    try:
        return get_llm(), None
    except Exception as e:
        return None, str(e)


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def _fmt_score(value: Any) -> str:
    if value is None:
        return "–"
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def _format_entry(item: Any) -> str:
    """Render one experience/education/project entry of arbitrary shape as markdown."""
    if not isinstance(item, dict):
        return str(item)
    title_keys = ("position", "title", "role", "degree", "name")
    org_keys = ("company", "organization", "institution", "university", "school")
    when_keys = ("duration", "dates", "year", "years", "period")

    def first(keys):
        for k in keys:
            if item.get(k):
                return str(item[k])
        return None

    head = " · ".join(x for x in (first(title_keys), first(org_keys), first(when_keys)) if x)
    used = set(title_keys + org_keys + when_keys)
    rest = []
    for k, v in item.items():
        if k in used or v in (None, "", []):
            continue
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v)
        rest.append(f"{v}" if k in ("description", "details", "summary") else f"*{k.replace('_', ' ')}:* {v}")
    text = f"**{head}**" if head else ""
    if rest:
        text += ("  \n" if text else "") + "  \n".join(rest)
    return text or str(item)


def render_score_breakdown(ranking: Dict[str, Any]):
    for category, max_score in SCORE_WEIGHTS.items():
        entry = ranking.get(category) or {}
        score = entry.get("score", 0) or 0
        st.markdown(f"**{CATEGORY_LABELS[category]}** — {_fmt_score(score)} / {max_score}")
        st.progress(min(1.0, max(0.0, float(score) / max_score)))
        if entry.get("justification"):
            st.caption(entry["justification"])


def render_candidate(resume: Dict[str, Any], ranking: Optional[Dict[str, Any]],
                     job_description: Optional[str] = None):
    left, right = st.columns([3, 2], gap="large")

    with left:
        contact = [
            ("✉️", resume.get("email_address")),
            ("📞", resume.get("contact_information")),
            ("🔗", resume.get("linkedin_profile")),
        ]
        line = "  ·  ".join(f"{icon} {value}" for icon, value in contact
                            if value and not isinstance(value, (dict, list)))
        if line:
            st.markdown(line)
        for icon, value in contact:
            if isinstance(value, dict):
                st.markdown(f"{icon} " + ", ".join(f"{v}" for v in value.values() if v))

        skills = resume.get("skills") or []
        if skills:
            st.markdown("**Skills**")
            st.markdown(" ".join(f":blue-badge[{s}]" for s in skills))

        for field, title in (("experience", "Experience"), ("education", "Education"),
                             ("projects", "Projects"), ("extras", "Extras")):
            items = resume.get(field) or []
            if items:
                st.markdown(f"**{title}**")
                for item in items:
                    st.markdown(_format_entry(item))

        if resume.get("source_file"):
            st.caption(f"Source file: {resume['source_file']}")

    with right:
        if ranking:
            st.metric("Match score", f"{_fmt_score(ranking.get('total_score'))} / 100")
            render_score_breakdown(ranking)
            if job_description:
                with st.popover("Job description used", width="stretch"):
                    st.write(job_description)
        else:
            st.info("This resume has not been ranked yet.")


def results_table(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """Build a leaderboard dataframe from (name, file, ranking) rows."""
    records = []
    for row in rows:
        ranking = row.get("ranking") or {}
        record = {
            "Candidate": row.get("name") or "Unknown",
            "Score": ranking.get("total_score"),
        }
        for category in SCORE_WEIGHTS:
            record[CATEGORY_LABELS[category]] = (ranking.get(category) or {}).get("score")
        record["File"] = row.get("file")
        records.append(record)
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values("Score", ascending=False, na_position="last").reset_index(drop=True)
        df.insert(0, "Rank", range(1, len(df) + 1))
    return df


TABLE_CONFIG = {
    "Rank": st.column_config.NumberColumn(width="small"),
    "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
    **{
        CATEGORY_LABELS[c]: st.column_config.NumberColumn(f"{CATEGORY_LABELS[c]} /{m}", format="%g")
        for c, m in SCORE_WEIGHTS.items()
    },
}


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
db, db_error = connect_db()
llm, llm_error = connect_llm()

with st.sidebar:
    st.title("🧭 HireWise")
    st.caption("AI resume screening and ranking")

    st.subheader("Status")
    if llm_error:
        st.error(f"Gemini: {llm_error}", icon="🔑")
    else:
        st.success(f"Gemini key configured · `{os.getenv('GEMINI_MODEL', DEFAULT_MODEL)}`", icon="✅")
    if db_error:
        st.error(f"MongoDB unavailable: {db_error}", icon="🗄️")
        if st.button("Retry connection"):
            get_db.clear()
            st.rerun()
    else:
        st.success(f"MongoDB connected · `{db.db.name}`", icon="✅")

    st.subheader("Scoring rubric")
    st.dataframe(
        pd.DataFrame({"Category": [CATEGORY_LABELS[c] for c in SCORE_WEIGHTS],
                      "Max": list(SCORE_WEIGHTS.values())}),
        hide_index=True, width="stretch",
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
st.title("Resume screening")
rank_tab, saved_tab = st.tabs(["📄 Rank resumes", "🗂️ Candidates"])

with rank_tab:
    job_description = st.text_area(
        "Job description",
        height=180,
        placeholder="Paste the job description here, e.g. requirements, responsibilities, nice-to-haves…",
    )
    uploads = st.file_uploader("Resumes (PDF)", type=["pdf"], accept_multiple_files=True)

    ready = bool(job_description.strip()) and bool(uploads) and db is not None and llm is not None
    if db is None or llm is None:
        st.warning("Fix the connection issues shown in the sidebar to start ranking.")

    if st.button("Analyze & rank", type="primary", disabled=not ready):
        results: List[Dict[str, Any]] = []
        progress = st.progress(0.0, text="Starting…")
        with st.status(f"Analyzing {len(uploads)} resume(s)…", expanded=True) as status:
            for i, upload in enumerate(uploads):
                progress.progress(i / len(uploads), text=f"Processing {upload.name} ({i + 1}/{len(uploads)})")
                st.write(f"📄 **{upload.name}** — parsing and scoring…")
                try:
                    result = process_resume_bytes(upload.getvalue(), upload.name,
                                                  job_description.strip(), db, llm=llm, verbose=False)
                except Exception as e:
                    result = {"file": upload.name, "name": None, "ranking": None,
                              "total_score": None, "resume": None, "error": str(e)}
                if result["error"]:
                    st.write(f"⚠️ {upload.name}: {result['error']}")
                else:
                    st.write(f"✅ {result['name']} — **{_fmt_score(result['total_score'])} / 100**")
                results.append(result)
            progress.progress(1.0, text="Done")
            failed = sum(1 for r in results if r["error"])
            status.update(
                label=f"Analyzed {len(results)} resume(s)" + (f" · {failed} with errors" if failed else ""),
                state="error" if failed == len(results) else "complete",
                expanded=bool(failed),
            )
        st.session_state["results"] = results
        st.session_state["results_jd"] = job_description.strip()

    results = st.session_state.get("results")
    if results:
        ranked = [r for r in results if r.get("ranking")]
        st.divider()
        st.subheader("Leaderboard")
        if ranked:
            scores = [r["total_score"] for r in ranked]
            c1, c2, c3 = st.columns(3)
            c1.metric("Candidates ranked", f"{len(ranked)} / {len(results)}")
            c2.metric("Top score", _fmt_score(max(scores)))
            c3.metric("Average score", f"{sum(scores) / len(scores):.1f}")
            st.dataframe(results_table(ranked), hide_index=True, width="stretch",
                         column_config=TABLE_CONFIG)

        for r in [r for r in results if r.get("error")]:
            st.error(f"**{r['file']}** — {r['error']}")

        st.subheader("Candidate details")
        ordered = sorted(ranked, key=lambda r: r["total_score"], reverse=True) + \
            [r for r in results if not r.get("ranking") and r.get("resume")]
        for i, r in enumerate(ordered):
            label = f"{r['name']} — {_fmt_score(r['total_score'])} / 100  ({r['file']})"
            with st.expander(label, expanded=(i == 0)):
                render_candidate(r["resume"], r.get("ranking"), st.session_state.get("results_jd"))

with saved_tab:
    if db is None:
        st.warning("MongoDB is not connected.")
    else:
        f1, f2 = st.columns([3, 1])
        search = f1.text_input("Search", placeholder="Name or skill, e.g. Python", label_visibility="collapsed")
        sort = f2.selectbox("Sort by", ["Highest score", "Newest"], label_visibility="collapsed")

        query: Dict[str, Any] = {}
        if search.strip():
            pattern = {"$regex": re.escape(search.strip()), "$options": "i"}
            query = {"$or": [{"name": pattern}, {"skills": pattern}]}

        sort_field = "total_score" if sort == "Highest score" else "created_at"
        try:
            docs = list(db.collection.find(query).sort([(sort_field, -1), ("created_at", -1)]).limit(200))
        except Exception as e:
            st.error(f"Could not load candidates: {e}")
            docs = []

        if not docs:
            st.info("No candidates found." if search else "No candidates yet — rank some resumes first.")
        else:
            table = pd.DataFrame([{
                "Candidate": d.get("name") or "Unknown",
                "Score": d.get("total_score"),
                "Email": d.get("email_address") if isinstance(d.get("email_address"), str) else None,
                "Skills": ", ".join(map(str, (d.get("skills") or [])[:8])),
                "Rankings": len(d.get("rankings") or []),
                "Added": d.get("created_at"),
            } for d in docs])
            st.caption(f"{len(docs)} candidate(s)")
            st.dataframe(table, hide_index=True, width="stretch", column_config={
                "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                "Added": st.column_config.DatetimeColumn("Added", format="YYYY-MM-DD HH:mm"),
            })

            options = {str(d["_id"]): d for d in docs}
            selected = st.selectbox(
                "View candidate",
                list(options),
                format_func=lambda i: f"{options[i].get('name') or 'Unknown'} — "
                                      f"{_fmt_score(options[i].get('total_score'))} / 100 "
                                      f"({options[i].get('source_file') or i})",
            )
            doc = options[selected]
            latest = doc.get("latest_ranking") or {}
            with st.container(border=True):
                st.subheader(doc.get("name") or "Unknown")
                render_candidate(doc, latest.get("ranking"), latest.get("job_description"))

                history = doc.get("rankings") or []
                if len(history) > 1:
                    with st.expander(f"Ranking history ({len(history)})"):
                        st.dataframe(pd.DataFrame([{
                            "Ranked at": h.get("ranked_at"),
                            "Score": (h.get("ranking") or {}).get("total_score"),
                            "Job description": (h.get("job_description") or "")[:120],
                        } for h in history]), hide_index=True, width="stretch")

                with st.popover("🗑️ Delete candidate"):
                    st.write(f"Permanently delete **{doc.get('name') or 'this candidate'}**?")
                    if st.button("Yes, delete", type="primary", key=f"del-{selected}"):
                        db.delete_resume(selected)
                        st.toast("Candidate deleted")
                        st.rerun()
