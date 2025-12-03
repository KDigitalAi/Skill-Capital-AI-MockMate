"""
Common/general-purpose interview endpoints
Contains shared endpoints used across multiple interview types
"""

from fastapi import APIRouter, HTTPException, Depends
from supabase import Client
from app.db.client import get_supabase_client
import re
from app.schemas.interview import (
    InterviewSetupRequest,
    InterviewSetupResponse,
    InterviewGenerateRequest,
    InterviewGenerateResponse,
    InterviewQuestion,
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    InterviewEvaluationRequest,
    InterviewEvaluationResponse,
    RolesResponse,
    ExperienceLevelsResponse,
    SessionQuestionsResponse,
    QuestionResponse,
    NextQuestionResponse
)
from app.services.topic_generator import topic_generator
from app.services.question_generator import question_generator
from app.services.answer_evaluator import answer_evaluator
from app.services.interview_evaluator import interview_evaluator
from app.routers.interview_utils import (
    log_interview_transcript,
    merge_resume_context,
    build_resume_context_from_profile,
    build_context_from_cache
)
from app.utils.request_validator import validate_request_size
from app.utils.rate_limiter import rate_limit_by_session_id
from fastapi import Request
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["interview"])


@router.post("/setup", response_model=InterviewSetupResponse)
async def setup_interview(
    http_request: Request,
    setup_request: InterviewSetupRequest,
    supabase: Client = Depends(get_supabase_client),
    _: None = Depends(validate_request_size)
):
    """
    Setup interview based on role and experience level.
    Generates interview topics based on user's skills from profile.
    """
    try:
        # Validate user_id format: alphanumeric, hyphen, underscore only
        if not re.match(r'^[a-zA-Z0-9_-]+$', setup_request.user_id):
            raise HTTPException(status_code=400, detail="Invalid user_id format")
        
        # Get user profile to fetch skills
        profile_response = supabase.table("user_profiles").select("*").eq("user_id", setup_request.user_id).execute()
        
        user_skills: Optional[list] = []
        if profile_response.data and len(profile_response.data) > 0:
            user_skills = profile_response.data[0].get("skills", [])
        
        # Generate topics based on role, experience, and user skills
        topics = topic_generator.generate_topics(
            role=setup_request.role,
            experience_level=setup_request.experience_level,
            user_skills=user_skills if user_skills else None
        )
        
        # Get suggested skills
        suggested_skills = topic_generator.get_suggested_skills(
            role=setup_request.role,
            user_skills=user_skills if user_skills else []
        )
        
        return InterviewSetupResponse(
            user_id=setup_request.user_id,
            role=setup_request.role,
            experience_level=setup_request.experience_level,
            topics=topics,
            suggested_skills=suggested_skills,
            total_topics=len(topics)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up interview: {str(e)}")


@router.get("/roles", response_model=RolesResponse)
async def get_available_roles():
    """Get list of available roles"""
    roles = [
        "Python Developer",
        "ServiceNow Engineer",
        "DevOps",
        "Fresher",
        "Full Stack Developer",
        "Data Engineer"
    ]
    return {"roles": roles}


@router.get("/experience-levels", response_model=ExperienceLevelsResponse)
async def get_experience_levels():
    """Get list of available experience levels"""
    levels = [
        "Fresher",
        "1yrs",
        "2yrs",
        "3yrs",
        "4yrs",
        "5yrs",
        "5yrs+"
    ]
    return {"experience_levels": levels}


@router.post("/generate", response_model=InterviewGenerateResponse)
async def generate_interview_questions(
    http_request: Request,
    generate_request: InterviewGenerateRequest,
    supabase: Client = Depends(get_supabase_client),
    _: None = Depends(validate_request_size)
):
    """
    Generate interview questions using OpenAI.
    Creates a session and stores questions in the database.
    If resume is uploaded, uses resume context for personalized questions.
    """
    try:
        # Validate user_id format: alphanumeric, hyphen, underscore only
        if not re.match(r'^[a-zA-Z0-9_-]+$', generate_request.user_id):
            raise HTTPException(status_code=400, detail="Invalid user_id format")
        
        profile_response = supabase.table("user_profiles").select("*").eq("user_id", generate_request.user_id).execute()
        profile = profile_response.data[0] if profile_response.data else None

        resume_context: Dict[str, Any] = {
            "skills": list(generate_request.skills),
            "experience_level": generate_request.experience_level,
            "projects": [],
            "keywords": {},
            "domains": []
        }
        if profile:
            resume_context = merge_resume_context(
                resume_context,
                build_resume_context_from_profile(profile, supabase)
            )

        # Try to supplement context from cached resume analysis if available
        try:
            from app.routers.profile import resume_analysis_cache
            cached_entry = None
            for cached_info in resume_analysis_cache.values():
                if cached_info.get("user_id") == generate_request.user_id:
                    cached_entry = cached_info
                    break
            if cached_entry:
                resume_context = merge_resume_context(
                    resume_context,
                    build_context_from_cache(cached_entry)
                )
        except Exception:
            pass

        if not resume_context.get("skills"):
            resume_context["skills"] = list(generate_request.skills)
        
        # Generate questions using AI (with resume context if available)
        questions = question_generator.generate_questions(
            role=generate_request.role,
            experience_level=generate_request.experience_level,
            skills=generate_request.skills,
            resume_context=resume_context
        )
        
        # Create interview session
        # Determine interview_type from role (default to 'full' for general interviews)
        interview_type = "full"  # Default for general interview setup
        if generate_request.role:
            role_lower = generate_request.role.lower()
            if "coding" in role_lower:
                interview_type = "coding"
            elif "technical" in role_lower:
                interview_type = "technical"
            elif "hr" in role_lower or "human resources" in role_lower:
                interview_type = "hr"
            elif "behavioral" in role_lower or "star" in role_lower:
                interview_type = "star"
        
        session_data = {
            "user_id": generate_request.user_id,
            "interview_type": interview_type,  # New schema field
            "role": generate_request.role,  # Keep for backward compatibility
            "experience_level": generate_request.experience_level,
            "skills": resume_context.get("skills", generate_request.skills),
            "session_status": "active"
        }
        
        session_response = supabase.table("interview_sessions").insert(session_data).execute()
        
        if not session_response.data or len(session_response.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to create interview session")
        
        session_id = session_response.data[0]["id"]
        
        # Note: In new schema, questions are stored in round tables when answers are submitted
        # We don't need to store questions separately anymore
        # Questions will be stored in technical_round, hr_round, or star_round when user submits answers
        
        return InterviewGenerateResponse(
            session_id=session_id,
            user_id=generate_request.user_id,
            role=generate_request.role,
            experience_level=generate_request.experience_level,
            questions=questions,
            total_questions=len(questions),
            created_at=datetime.now()
        )
        
    except ValueError as e:
        # If OpenAI key is not set, return fallback questions
        if "OpenAI API key" in str(e):
            # Use fallback questions
            questions = question_generator._get_fallback_questions(
                role=generate_request.role,
                experience_level=generate_request.experience_level,
                skills=generate_request.skills,
                resume_context=resume_context
            )
            
            # Still create session and store questions
            # Determine interview_type from role
            interview_type = "full"  # Default
            if generate_request.role:
                role_lower = generate_request.role.lower()
                if "coding" in role_lower:
                    interview_type = "coding"
                elif "technical" in role_lower:
                    interview_type = "technical"
                elif "hr" in role_lower or "human resources" in role_lower:
                    interview_type = "hr"
                elif "behavioral" in role_lower or "star" in role_lower:
                    interview_type = "star"
            
            session_data = {
                "user_id": generate_request.user_id,
                "interview_type": interview_type,  # New schema field
                "role": generate_request.role,  # Keep for backward compatibility
                "experience_level": generate_request.experience_level,
                "skills": resume_context.get("skills", generate_request.skills),
                "session_status": "active"
            }
            
            session_response = supabase.table("interview_sessions").insert(session_data).execute()
            session_id = session_response.data[0]["id"] if session_response.data else str(uuid.uuid4())
            
            # Note: In new schema, questions are stored in round tables when answers are submitted
            # We don't store questions separately in interview_questions table anymore
            # Questions will be stored in the appropriate round table (technical_round, hr_round, star_round) when user submits answers
            logger.info(f"[INTERVIEW][SETUP] Generated {len(questions)} questions for session {session_id}. Questions will be stored in round tables when answers are submitted.")
            
            return InterviewGenerateResponse(
                session_id=session_id,
                user_id=generate_request.user_id,
                role=generate_request.role,
                experience_level=generate_request.experience_level,
                questions=questions,
                total_questions=len(questions),
                created_at=datetime.now()
            )
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating interview questions: {str(e)}")


@router.get("/session/{session_id}/questions", response_model=SessionQuestionsResponse)
async def get_session_questions(
    session_id: str,
    supabase: Client = Depends(get_supabase_client),
    _: None = Depends(rate_limit_by_session_id)
):
    """Get all questions for a specific interview session"""
    try:
        # Get session
        session_response = supabase.table("interview_sessions").select("*").eq("id", session_id).execute()
        
        if not session_response.data or len(session_response.data) == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get questions from appropriate round table based on session type (new schema)
        session = session_response.data[0]
        session_type = session.get("interview_type", "technical")
        
        # Determine which round table to use
        if session_type == "coding":
            round_table = "coding_round"
        elif session_type == "hr":
            round_table = "hr_round"
        elif session_type == "star":
            round_table = "star_round"
        else:
            round_table = "technical_round"
        
        # Get questions from round table
        questions_response = supabase.table(round_table).select("question_text, question_type, question_number").eq("session_id", session_id).order("question_number").execute()
        
        questions = []
        if questions_response.data:
            for q in questions_response.data:
                question_text = q.get("question_text", "")
                if question_text:  # Only include if question text exists
                    questions.append(InterviewQuestion(
                        type=q.get("question_type", "Technical"),
                        question=question_text
                    ))
        
        return SessionQuestionsResponse(
            session_id=session_id,
            session=session_response.data[0],
            questions=questions,
            total_questions=len(questions)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching session questions: {str(e)}")


@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(
    http_request: Request,
    start_request: StartInterviewRequest,
    supabase: Client = Depends(get_supabase_client),
    _: None = Depends(validate_request_size)
):
    """Start an interview session - get the first question"""
    try:
        # Get session
        session_response = supabase.table("interview_sessions").select("*").eq("id", start_request.session_id).execute()
        
        if not session_response.data or len(session_response.data) == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_response.data[0]
        
        # Get first question from appropriate round table (new schema)
        session_type = session.get("interview_type", "technical")
        
        # Determine which round table to use
        if session_type == "coding":
            round_table = "coding_round"
        elif session_type == "hr":
            round_table = "hr_round"
        elif session_type == "star":
            round_table = "star_round"
        else:
            round_table = "technical_round"
        
        questions_response = supabase.table(round_table).select("question_text, question_type, question_number").eq("session_id", start_request.session_id).order("question_number").limit(1).execute()
        
        if not questions_response.data or len(questions_response.data) == 0:
            raise HTTPException(status_code=404, detail="No questions found for this session")
        
        first_question_row = questions_response.data[0]
        first_question = {
            "question_type": first_question_row.get("question_type", "Technical"),
            "question": first_question_row.get("question_text", ""),
            "question_number": first_question_row.get("question_number", 1)
        }
        
        # Get total question count
        total_response = supabase.table(round_table).select("question_number").eq("session_id", start_request.session_id).execute()
        total_questions = len(total_response.data) if total_response.data else 1
        
        # Update session status to active if needed (atomic update with row-level locking)
        if session.get("session_status") != "active":
            supabase.table("interview_sessions").update({"session_status": "active"}).eq("id", start_request.session_id).neq("session_status", "active").execute()
        
        return StartInterviewResponse(
            session_id=start_request.session_id,
            current_question=InterviewQuestion(
                type=first_question.get("question_type", "Technical"),
                question=first_question.get("question", "")
            ),
            question_number=first_question.get("question_number", 1),
            total_questions=total_questions,
            interview_started=True,
            time_limit=60  # 60 seconds per question
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting interview: {str(e)}")


@router.get("/session/{session_id}/question/{question_number}", response_model=QuestionResponse)
async def get_question(
    session_id: str,
    question_number: int,
    supabase: Client = Depends(get_supabase_client),
    _: None = Depends(rate_limit_by_session_id)
):
    """Get a specific question by number"""
    try:
        # Get session to determine which round table to use
        session_response = supabase.table("interview_sessions").select("interview_type").eq("id", session_id).execute()
        if not session_response.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_type = session_response.data[0].get("interview_type", "technical")
        
        # Determine which round table to use
        if session_type == "coding":
            round_table = "coding_round"
        elif session_type == "hr":
            round_table = "hr_round"
        elif session_type == "star":
            round_table = "star_round"
        else:
            round_table = "technical_round"
        
        questions_response = supabase.table(round_table).select("*").eq("session_id", session_id).eq("question_number", question_number).execute()
        
        if not questions_response.data or len(questions_response.data) == 0:
            raise HTTPException(status_code=404, detail="Question not found")
        
        question = questions_response.data[0]
        
        return QuestionResponse(
            question_id=question.get("id"),
            question_number=question.get("question_number", question_number),
            question_type=question.get("question_type", "Technical"),
            question=question.get("question_text", "")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching question: {str(e)}")


@router.post("/submit-answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    http_request: Request,
    answer_request: SubmitAnswerRequest,
    supabase: Client = Depends(get_supabase_client),
    _: None = Depends(validate_request_size)
):
    """Submit an answer and get AI evaluation"""
    try:
        # Get session to get experience level
        session_response = supabase.table("interview_sessions").select("*").eq("id", answer_request.session_id).execute()
        
        if not session_response.data or len(session_response.data) == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_response.data[0]
        experience_level = session.get("experience_level", "Fresher")
        
        # Evaluate answer using AI (include response time in evaluation)
        scores = answer_evaluator.evaluate_answer(
            question=answer_request.question_text,
            question_type=answer_request.question_type,
            answer=answer_request.user_answer,
            experience_level=experience_level,
            response_time=answer_request.response_time
        )
        
        # Store answer in database
        answer_data = {
            "session_id": answer_request.session_id,
            "question_id": answer_request.question_id,
            "question_number": answer_request.question_number,
            "question_text": answer_request.question_text,
            "question_type": answer_request.question_type,
            "user_answer": answer_request.user_answer,
            "relevance_score": scores.relevance,
            "confidence_score": scores.confidence,
            "technical_accuracy_score": scores.technical_accuracy,
            "communication_score": scores.communication,
            "overall_score": scores.overall,
            "ai_feedback": scores.feedback,
            "response_time": answer_request.response_time,
            "evaluated_at": datetime.now().isoformat()
        }
        
        # Determine which round table to use based on question_type
        # For now, default to technical_round (can be enhanced later for HR/STAR)
        round_table = "technical_round"
        if answer_request.question_type:
            question_type_lower = answer_request.question_type.lower()
            if "hr" in question_type_lower or "human resources" in question_type_lower:
                round_table = "hr_round"
            elif "star" in question_type_lower or "behavioral" in question_type_lower:
                round_table = "star_round"
        
        # Map answer_data to the correct table structure based on round type
        user_id = str(session.get("user_id", ""))
        
        if round_table == "technical_round":
            round_data = {
                "user_id": user_id,
                "session_id": answer_request.session_id,
                "question_number": answer_request.question_number,
                "question_text": answer_request.question_text,
                "question_type": answer_request.question_type,
                "user_answer": answer_request.user_answer,
                "relevance_score": scores.relevance,
                "technical_accuracy_score": scores.technical_accuracy,
                "communication_score": scores.communication,
                "overall_score": scores.overall,
                "ai_feedback": scores.feedback,
                "ai_response": scores.feedback,  # Use feedback as ai_response
                "response_time": answer_request.response_time
                # Note: confidence_score not in technical_round schema, using communication_score instead
            }
        elif round_table == "hr_round":
            round_data = {
                "user_id": user_id,
                "session_id": answer_request.session_id,
                "question_number": answer_request.question_number,
                "question_text": answer_request.question_text,
                "question_category": answer_request.question_type,
                "user_answer": answer_request.user_answer,
                "communication_score": scores.communication,
                "cultural_fit_score": scores.relevance,  # Map relevance to cultural fit
                "motivation_score": scores.communication,  # Map communication to motivation (confidence_score not in schema)
                "clarity_score": scores.communication,
                "overall_score": scores.overall,
                "ai_feedback": scores.feedback,
                "response_time": answer_request.response_time
            }
        else:  # star_round
            round_data = {
                "user_id": user_id,
                "session_id": answer_request.session_id,
                "question_number": answer_request.question_number,
                "question_text": answer_request.question_text,
                "user_answer": answer_request.user_answer,
                "star_structure_score": scores.overall,  # Use overall as structure score
                "situation_score": scores.relevance,  # Map relevance to situation
                "task_score": scores.communication,  # Map communication to task
                "action_score": scores.technical_accuracy,  # Map technical to action
                "result_score": scores.overall,  # Use overall for result
                "overall_score": scores.overall,
                "ai_feedback": scores.feedback,
                "response_time": answer_request.response_time
            }
        
        # Check if row already exists (question was stored when it was asked)
        existing_row = supabase.table(round_table).select("id").eq("session_id", answer_request.session_id).eq("question_number", answer_request.question_number).execute()
        
        if existing_row.data and len(existing_row.data) > 0:
            # Update existing row with answer and evaluation
            answer_response = supabase.table(round_table).update(round_data).eq("session_id", answer_request.session_id).eq("question_number", answer_request.question_number).execute()
        else:
            # Insert new row if question wasn't stored earlier (fallback)
            answer_response = supabase.table(round_table).insert(round_data).execute()
        
        if not answer_response.data or len(answer_response.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to save answer")
        
        await log_interview_transcript(
            supabase,
            answer_request.session_id,
            "technical",
            answer_request.question_text,
            answer_request.user_answer
        )
        
        answer_id = answer_response.data[0]["id"]
        # Get created_at timestamp from response (new schema uses created_at instead of answered_at)
        created_at_str = answer_response.data[0].get("created_at")
        if isinstance(created_at_str, str):
            created_at_str = created_at_str.replace('Z', '+00:00')
            try:
                answered_at = datetime.fromisoformat(created_at_str)
            except ValueError:
                answered_at = datetime.now()
        else:
            answered_at = datetime.now()
        evaluated_at = datetime.now()
        
        return SubmitAnswerResponse(
            answer_id=answer_id,
            session_id=answer_request.session_id,
            question_id=answer_request.question_id,
            scores=scores,
            response_time=answer_request.response_time,
            answered_at=answered_at,
            evaluated_at=evaluated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting answer: {str(e)}")


@router.get("/session/{session_id}/next-question/{current_question_number}", response_model=NextQuestionResponse)
async def get_next_question(
    session_id: str,
    current_question_number: int,
    supabase: Client = Depends(get_supabase_client),
    _: None = Depends(rate_limit_by_session_id)
):
    """Get the next question after the current one (legacy endpoint - uses new schema)"""
    try:
        # Get session to determine which round table to use
        session_response = supabase.table("interview_sessions").select("interview_type").eq("id", session_id).execute()
        if not session_response.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_type = session_response.data[0].get("interview_type", "technical")
        
        # Determine which round table to use
        if session_type == "coding":
            round_table = "coding_round"
        elif session_type == "hr":
            round_table = "hr_round"
        elif session_type == "star":
            round_table = "star_round"
        else:
            round_table = "technical_round"
        
        # Get next question from round table
        questions_response = supabase.table(round_table).select("question_text, question_type, question_number").eq("session_id", session_id).gt("question_number", current_question_number).order("question_number").limit(1).execute()
        
        if not questions_response.data or len(questions_response.data) == 0:
            # No more questions
            # Mark session as completed (atomic update with row-level locking)
            supabase.table("interview_sessions").update({"session_status": "completed"}).eq("id", session_id).neq("session_status", "completed").execute()
            return NextQuestionResponse(
                has_next=False,
                message="Interview completed! No more questions."
            )
        
        question = questions_response.data[0]
        
        return NextQuestionResponse(
            has_next=True,
            question_id=question.get("id"),
            question_number=question.get("question_number", current_question_number + 1),
            question_type=question.get("question_type", "Technical"),
            question=question.get("question_text", "")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching next question: {str(e)}")


@router.post("/evaluate", response_model=InterviewEvaluationResponse)
async def evaluate_interview(
    http_request: Request,
    evaluation_request: InterviewEvaluationRequest,
    supabase: Client = Depends(get_supabase_client),
    _: None = Depends(validate_request_size)
):
    """Evaluate complete interview session and generate feedback report"""
    try:
        # Get session
        session_response = supabase.table("interview_sessions").select("*").eq("id", evaluation_request.session_id).execute()
        
        if not session_response.data or len(session_response.data) == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_response.data[0]
        role = session.get("role", "Unknown")
        experience_level = session.get("experience_level", "Fresher")
        
        # Get all answers for this session (check session type to determine which table)
        # For now, default to technical_round (can be enhanced later)
        session_type = session.get("interview_type", "technical") if session else "technical"
        if session_type == "coding":
            round_table = "coding_round"
        elif session_type == "hr":
            round_table = "hr_round"
        elif session_type == "star":
            round_table = "star_round"
        else:
            round_table = "technical_round"
        
        answers_response = supabase.table(round_table).select("*").eq("session_id", evaluation_request.session_id).order("question_number").execute()
        
        answers = answers_response.data if answers_response.data else []
        
        if not answers:
            raise HTTPException(status_code=400, detail="No answers found for this session. Please complete the interview first.")
        
        # Get total questions count from round table (questions are stored there)
        # Count unique question_numbers in answers
        total_questions = len(answers) if answers else 0
        
        # Evaluate interview
        evaluation_result = interview_evaluator.evaluate_interview(
            role=role,
            experience_level=experience_level,
            answers=answers,
            total_questions=total_questions
        )
        
        return InterviewEvaluationResponse(
            session_id=evaluation_request.session_id,
            overall_score=evaluation_result["overall_score"],
            category_scores=evaluation_result["category_scores"],
            total_questions=total_questions,
            answered_questions=len(answers),
            feedback_summary=evaluation_result["feedback_summary"],
            recommendations=evaluation_result["recommendations"],
            strengths=evaluation_result["strengths"],
            areas_for_improvement=evaluation_result["areas_for_improvement"],
            generated_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating interview: {str(e)}")

