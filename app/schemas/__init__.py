"""
Pydantic schemas for request/response validation
"""

from .user import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse
)

from .interview import (
    InterviewSetupRequest,
    InterviewSetupResponse,
    InterviewTopic,
    InterviewQuestion,
    InterviewGenerateRequest,
    InterviewGenerateResponse,
    AnswerScore,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    CategoryScore,
    InterviewEvaluationRequest,
    InterviewEvaluationResponse
)


from .dashboard import (
    InterviewSummary,
    SkillAnalysis,
    TrendDataPoint,
    PerformanceDashboardResponse,
    TrendsDashboardResponse
)

__all__ = [
    # User schemas
    "UserProfileCreate",
    "UserProfileUpdate",
    "UserProfileResponse",
    # Interview schemas
    "InterviewSetupRequest",
    "InterviewSetupResponse",
    "InterviewTopic",
    "InterviewQuestion",
    "InterviewGenerateRequest",
    "InterviewGenerateResponse",
    "AnswerScore",
    "SubmitAnswerRequest",
    "SubmitAnswerResponse",
    "StartInterviewRequest",
    "StartInterviewResponse",
    "CategoryScore",
    "InterviewEvaluationRequest",
    "InterviewEvaluationResponse",
    # Dashboard schemas
    "InterviewSummary",
    "SkillAnalysis",
    "TrendDataPoint",
    "PerformanceDashboardResponse",
    "TrendsDashboardResponse"
]

