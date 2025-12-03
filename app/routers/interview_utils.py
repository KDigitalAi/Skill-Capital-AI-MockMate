"""
Shared utilities for interview routers
Contains helper functions and constants used across multiple interview types
"""

from supabase import Client
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import tempfile
import os
from app.services.resume_parser import resume_parser

logger = logging.getLogger(__name__)

# HR Interview Warm-up Questions - Always asked first (questions 1-3)
HR_WARMUP_QUESTIONS = [
    "Tell me about yourself.",
    "What are your greatest strengths and weaknesses?",
    "Why should we hire you?"
]
HR_WARMUP_COUNT = len(HR_WARMUP_QUESTIONS)  # 3 questions


def test_supabase_connection(supabase: Client) -> bool:
    """
    Test the Supabase connection by performing a simple query.
    Returns True if connection is successful, False otherwise.
    """
    try:
        # Perform a simple query to test connection
        supabase.table("interview_sessions").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"[CONNECTION TEST] Database connection test failed: {str(e)}", exc_info=True)
        return False


async def log_interview_transcript(
    supabase: Client,
    session_id: Optional[str],
    interview_type: str,
    question_text: Optional[str],
    user_answer: Optional[str] = None
) -> None:
    """
    Store each question/answer interaction in Supabase for analytics
    """
    if not supabase:
        return
    if not session_id:
        session_id = "unknown_session"

    try:
        transcript_data = {
            "session_id": session_id,
            "interview_type": interview_type,
            "question": question_text or "",
            "user_answer": user_answer,
            "created_at": datetime.utcnow().isoformat()
        }
        supabase.table("interview_transcripts").insert(transcript_data).execute()
    except Exception as e:
        pass  # Silently fail transcript logging to not interrupt interview flow


def _normalize_project_entries(project_entries: Optional[Any]) -> List[str]:
    """Convert parsed project data into human-readable strings"""
    normalized: List[str] = []
    if not project_entries:
        return normalized
    try:
        for entry in project_entries:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("title") or entry.get("project")
                description = entry.get("summary") or entry.get("description")
                technologies = entry.get("technologies") or entry.get("tech")
                parts = []
                if name:
                    parts.append(name.strip())
                if description:
                    parts.append(description.strip())
                if technologies and isinstance(technologies, list):
                    parts.append(f"Tech: {', '.join(technologies[:4])}")
                project_text = " - ".join(parts)
                if project_text:
                    normalized.append(project_text)
            elif isinstance(entry, str):
                project_text = entry.strip()
                if project_text:
                    normalized.append(project_text)
    except Exception as err:
        logger.warning(f"Could not normalize projects: {err}")
    return normalized[:5]


def build_resume_context_from_profile(
    profile_row: Optional[Dict[str, Any]],
    supabase: Client
) -> Dict[str, Any]:
    """
    Build a resume-aware context dictionary from the stored profile + resume file
    """
    context: Dict[str, Any] = {
        "skills": [],
        "experience_level": None,
        "projects": [],
        "keywords": {},
        "domains": []
    }
    if not profile_row:
        return context

    context["skills"] = list(profile_row.get("skills", []) or [])
    # Set experience_level from profile, but validate it
    profile_experience = profile_row.get("experience_level")
    if profile_experience and profile_experience not in ["Not specified", "Unknown"]:
        context["experience_level"] = profile_experience
    else:
        # Default to Fresher if not specified or invalid
        context["experience_level"] = "Fresher"

    resume_url = profile_row.get("resume_url")
    if resume_url and "storage/v1/object/public/" in resume_url:
        tmp_file_path = None
        try:
            path_part = resume_url.split("storage/v1/object/public/")[1]
            bucket_name = path_part.split("/")[0]
            file_path = "/".join(path_part.split("/")[1:])

            file_response = supabase.storage.from_(bucket_name).download(file_path)
            if file_response:
                file_extension = os.path.splitext(file_path)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                    tmp_file.write(file_response)
                    tmp_file_path = tmp_file.name

                parsed_resume = resume_parser.parse_resume(tmp_file_path, file_extension)
                parsed_skills = parsed_resume.get("skills", [])
                if parsed_skills:
                    existing = set(s.lower() for s in context["skills"])
                    for skill in parsed_skills:
                        if skill and skill.lower() not in existing:
                            context["skills"].append(skill)
                            existing.add(skill.lower())
                context["keywords"] = parsed_resume.get("keywords", {})
                summary_block = parsed_resume.get("summary") or {}
                projects_list = summary_block.get("projects_summary") or parsed_resume.get("projects")
                if projects_list:
                    context["projects"] = _normalize_project_entries(projects_list)
                # Only set experience_level if it's not already set and if it's a valid work experience
                parsed_experience = parsed_resume.get("experience_level")
                if not context.get("experience_level"):
                    # Ensure parsed experience is valid (not inferred from projects)
                    if parsed_experience and parsed_experience not in ["Not specified", "Unknown"]:
                        # Double-check: if it's "Fresher", use it; otherwise verify it's from work experience
                        if parsed_experience == "Fresher":
                            context["experience_level"] = "Fresher"
                        elif parsed_experience and parsed_experience != "Fresher":
                            # Only use if it's a valid work experience (contains "yrs" or years)
                            if "yrs" in parsed_experience.lower() or "years" in parsed_experience.lower() or "yr" in parsed_experience.lower():
                                context["experience_level"] = parsed_experience
                            else:
                                # If it doesn't look like valid work experience, default to Fresher
                                context["experience_level"] = "Fresher"
                    else:
                        # If no valid experience found, default to Fresher
                        context["experience_level"] = "Fresher"
                domains = context["keywords"].get("job_titles", []) if context["keywords"] else []
                if domains:
                    context["domains"] = domains
        except Exception as err:
            logger.warning(f"Failed to parse resume for context: {err}")
        finally:
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except Exception:
                    pass

    return context


def build_context_from_cache(cache_entry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not cache_entry:
        return {}
    summary_block = cache_entry.get("summary") or {}
    projects_list = summary_block.get("projects_summary")
    context = {
        "skills": cache_entry.get("skills", []) or [],
        "projects": _normalize_project_entries(projects_list),
        "experience_level": cache_entry.get("experience_level"),
        "keywords": cache_entry.get("keywords", {}),
        "domains": []
    }
    interview_modules = cache_entry.get("interview_modules") or {}
    if not context["projects"]:
        coding_module = interview_modules.get("coding_test") if isinstance(interview_modules, dict) else None
        if coding_module:
            topics = coding_module.get("topics")
            if topics:
                context["projects"] = [f"Coding Topic: {topic}" for topic in topics[:3]]
    return context


def merge_resume_context(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    if not extra:
        return base
    merged = {
        "skills": list(dict.fromkeys((base.get("skills") or []) + (extra.get("skills") or []))),
        "projects": list(dict.fromkeys((base.get("projects") or []) + (extra.get("projects") or []))),
        "experience_level": base.get("experience_level") or extra.get("experience_level"),
        "keywords": base.get("keywords") or extra.get("keywords") or {},
        "domains": list(dict.fromkeys((base.get("domains") or []) + (extra.get("domains") or [])))
    }

    # Merge keyword dictionaries if both exist
    if base.get("keywords") and extra.get("keywords"):
        merged["keywords"] = {**extra.get("keywords", {}), **base.get("keywords", {})}
    return merged

