"""
Interview-related schemas
Pydantic models for interview requests and responses
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class InterviewSetupRequest(BaseModel):
    """
    Schema for interview setup request
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    user_id: str
    role: str
    experience_level: str


class InterviewTopic(BaseModel):
    """
    Schema for interview topic
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    topic: str
    description: str
    category: str  # e.g., "Technical", "Behavioral", "System Design"


class InterviewSetupResponse(BaseModel):
    """
    Schema for interview setup response
    Time Complexity: O(1)
    Space Complexity: O(n) where n = number of topics
    """
    user_id: str
    role: str
    experience_level: str
    topics: List[InterviewTopic]
    suggested_skills: List[str]
    total_topics: int


class InterviewQuestion(BaseModel):
    """
    Schema for interview question
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    type: str  # HR, Technical, Problem-solving
    question: str


class InterviewGenerateRequest(BaseModel):
    """
    Schema for interview question generation request
    Time Complexity: O(1)
    Space Complexity: O(n) where n = number of skills
    """
    user_id: str
    role: str
    experience_level: str
    skills: List[str]


class InterviewGenerateResponse(BaseModel):
    """
    Schema for interview question generation response
    Time Complexity: O(1)
    Space Complexity: O(n) where n = number of questions
    """
    session_id: str
    user_id: str
    role: str
    experience_level: str
    questions: List[InterviewQuestion]
    total_questions: int
    created_at: datetime


class AnswerScore(BaseModel):
    """
    Schema for answer scoring
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    relevance: int  # 0-100
    confidence: int  # 0-100
    technical_accuracy: int  # 0-100
    communication: int  # 0-100
    overall: int  # Average score
    feedback: str  # AI-generated feedback


class SubmitAnswerRequest(BaseModel):
    """
    Schema for submitting an answer
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    session_id: str
    question_id: str
    question_number: int
    question_text: str
    question_type: str
    user_answer: str
    response_time: Optional[int] = None  # Response time in seconds


class SubmitAnswerResponse(BaseModel):
    """
    Schema for answer submission response
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    answer_id: str
    session_id: str
    question_id: str
    scores: AnswerScore
    response_time: Optional[int] = None
    answered_at: datetime
    evaluated_at: datetime


class StartInterviewRequest(BaseModel):
    """
    Schema for starting an interview
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    session_id: str


class StartInterviewResponse(BaseModel):
    """
    Schema for starting interview response
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    session_id: str
    current_question: InterviewQuestion
    question_number: int
    total_questions: int
    interview_started: bool
    time_limit: int = 60  # Time limit per question in seconds


class CategoryScore(BaseModel):
    """
    Schema for category scores
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    clarity: float  # Weighted average
    accuracy: float  # Weighted average (technical_accuracy)
    confidence: float  # Weighted average
    communication: float  # Weighted average


class InterviewEvaluationRequest(BaseModel):
    """
    Schema for interview evaluation request
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    session_id: str


class InterviewEvaluationResponse(BaseModel):
    """
    Schema for interview evaluation response
    Time Complexity: O(1)
    Space Complexity: O(n) where n = number of recommendations/strengths
    """
    session_id: str
    overall_score: float
    category_scores: CategoryScore
    total_questions: int
    answered_questions: int
    feedback_summary: str
    recommendations: List[str]
    strengths: List[str]
    areas_for_improvement: List[str]
    generated_at: datetime


class TechnicalInterviewStartRequest(BaseModel):
    """
    Schema for starting a technical interview
    """
    user_id: str


class TechnicalInterviewStartResponse(BaseModel):
    """
    Schema for technical interview start response
    """
    session_id: str
    question: str
    question_type: str
    question_number: int
    total_questions: int
    skills: List[str]
    audio_url: Optional[str] = None
    interview_completed: bool
    user_id: str


class HRInterviewStartResponse(BaseModel):
    """
    Schema for HR interview start response
    """
    session_id: str
    question: str
    question_type: str
    question_number: int
    total_questions: int
    interview_completed: bool
    is_warmup: bool
    user_id: str
    audio_url: Optional[str] = None


class STARInterviewStartResponse(BaseModel):
    """
    Schema for STAR interview start response
    """
    session_id: str
    question: str
    question_type: str
    question_number: int
    total_questions: int
    user_id: str
    audio_url: Optional[str] = None


class CodingQuestion(BaseModel):
    """
    Schema for coding question object
    """
    problem: Optional[str] = None
    question: Optional[str] = None
    difficulty: Optional[str] = None
    question_number: Optional[int] = None
    
    class Config:
        extra = "allow"  # Allow extra fields that may exist in question object


class CodingInterviewStartResponse(BaseModel):
    """
    Schema for coding interview start response
    """
    session_id: str
    question: CodingQuestion
    question_number: int
    total_questions: int
    skills: List[str]
    interview_completed: bool
    user_id: str


# Response models for submit-answer endpoints
class HRSubmitAnswerResponse(BaseModel):
    """Schema for HR submit answer response"""
    answer_id: Optional[str] = None
    session_id: str
    question_number: int
    scores: Dict[str, int]  # communication, cultural_fit, motivation, clarity, overall
    ai_response: Optional[str] = None
    audio_url: Optional[str] = None
    feedback: Optional[str] = None
    interview_completed: bool
    response_time: Optional[int] = None
    answered_at: Optional[str] = None


class TechnicalSubmitAnswerResponse(BaseModel):
    """Schema for technical submit answer response"""
    answer_id: Optional[str] = None
    session_id: str
    question_number: int
    scores: Dict[str, int]  # relevance, technical_accuracy, communication, overall
    ai_response: Optional[str] = None
    audio_url: Optional[str] = None
    interview_completed: bool


class STARSubmitAnswerResponse(BaseModel):
    """Schema for STAR submit answer response"""
    answer_id: Optional[str] = None
    session_id: str
    question_number: int
    scores: Dict[str, int]  # star_structure, situation, task, action, result, overall
    ai_response: Optional[str] = None
    audio_url: Optional[str] = None
    feedback: Optional[str] = None
    interview_completed: bool
    response_time: Optional[int] = None


# Response models for next-question endpoints
class HRNextQuestionResponse(BaseModel):
    """Schema for HR next question response"""
    question: Optional[str] = None  # May be None if interview_completed
    question_type: Optional[str] = None
    question_number: Optional[int] = None
    total_questions: Optional[int] = None
    audio_url: Optional[str] = None
    interview_completed: bool
    session_id: Optional[str] = None
    is_warmup: Optional[bool] = None
    message: Optional[str] = None  # For completion message


class TechnicalNextQuestionResponse(BaseModel):
    """Schema for technical next question response"""
    question: Optional[str] = None  # May be None if interview_completed
    question_type: Optional[str] = None
    question_number: Optional[int] = None
    total_questions: Optional[int] = None
    audio_url: Optional[str] = None
    interview_completed: bool
    session_id: Optional[str] = None
    message: Optional[str] = None  # For completion message


class STARNextQuestionResponse(BaseModel):
    """Schema for STAR next question response"""
    question: Optional[str] = None  # May be None if interview_completed
    question_type: Optional[str] = None
    question_number: Optional[int] = None
    total_questions: Optional[int] = None
    audio_url: Optional[str] = None
    interview_completed: bool
    session_id: Optional[str] = None
    message: Optional[str] = None  # For completion message


class CodingNextQuestionResponse(BaseModel):
    """Schema for coding next question response"""
    question: Dict[str, Any]  # CodingQuestion object as dict
    question_number: int
    total_questions: int
    interview_completed: bool
    session_id: str
    user_id: Optional[str] = None


# Response models for end endpoints
class InterviewEndResponse(BaseModel):
    """Schema for interview end response"""
    message: str
    session_id: str
    status: Optional[str] = None


# Response models for run endpoint
class CodeRunResponse(BaseModel):
    """Schema for code execution response"""
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: float
    exit_code: Optional[int] = None
    note: Optional[str] = None  # For Vercel serverless note


# Response models for speech endpoints
class SpeechToTextResponse(BaseModel):
    """Schema for speech-to-text response"""
    text: str
    language: str


# Response models for feedback endpoints
class HRFeedbackResponse(BaseModel):
    """Schema for HR feedback response"""
    overall_score: float
    communication_score: float
    cultural_fit_score: float
    motivation_score: float
    clarity_score: float
    feedback_summary: str
    strengths: List[str]
    areas_for_improvement: List[str]
    recommendations: List[str]
    question_count: Optional[int] = None


class TechnicalFeedbackResponse(BaseModel):
    """Schema for technical feedback response - matches generate_final_feedback return"""
    overall_score: float
    strengths: List[str]
    areas_for_improvement: List[str]
    recommendations: List[str]
    feedback_summary: str
    session_id: Optional[str] = None


class STARFeedbackResponse(BaseModel):
    """Schema for STAR feedback response"""
    overall_score: float
    situation_score: float
    task_score: float
    action_score: float
    result_score: float
    star_structure_score: float
    feedback_summary: str
    strengths: List[str]
    areas_for_improvement: List[str]
    recommendations: List[str]
    question_count: Optional[int] = None


# Response models for summary and results
class TechnicalSummaryResponse(BaseModel):
    """Schema for technical interview summary response"""
    session_id: str
    total_questions: int
    answered_questions: int
    unanswered_questions: Optional[int] = None
    overall_score: Optional[float] = None
    strengths: Optional[List[str]] = None
    weak_areas: Optional[List[str]] = None  # Some endpoints use weak_areas instead of areas_for_improvement
    areas_for_improvement: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    summary: Optional[str] = None


class CodingResultItem(BaseModel):
    """Schema for a single coding result item"""
    question_number: int
    question_text: str
    user_code: str
    correctness: bool
    final_score: int
    programming_language: str
    difficulty_level: str
    errors_found: List[str]
    bugs_explained: List[str]
    improvements: List[str]
    motivation_message: str
    time_complexity: str
    space_complexity: str


class CodingResultsResponse(BaseModel):
    """Schema for coding results response"""
    session_id: str
    results: List[CodingResultItem]
    statistics: Dict[str, Any]  # total_questions, correct_answers, incorrect_answers, total_score, average_score, accuracy


class RolesResponse(BaseModel):
    """Schema for roles list response"""
    roles: List[str]


class ExperienceLevelsResponse(BaseModel):
    """Schema for experience levels list response"""
    experience_levels: List[str]


class SessionQuestionsResponse(BaseModel):
    """Schema for session questions response"""
    session_id: str
    session: Dict[str, Any]
    questions: List[InterviewQuestion]
    total_questions: int


class QuestionResponse(BaseModel):
    """Schema for single question response"""
    question_id: Optional[str] = None
    question_number: int
    question_type: str
    question: str


class NextQuestionResponse(BaseModel):
    """Schema for next question response"""
    has_next: bool
    message: Optional[str] = None
    question_id: Optional[str] = None
    question_number: Optional[int] = None
    question_type: Optional[str] = None
    question: Optional[str] = None
