"""
Pydantic schemas for request/response validation
"""

from .user import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
    ResumeAnalysisResponse,
    ResumeUploadResponse,
    ExperienceUpdateResponse
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
    InterviewEvaluationResponse,
    TechnicalInterviewStartRequest,
    TechnicalInterviewStartResponse,
    HRInterviewStartResponse,
    STARInterviewStartResponse,
    CodingQuestion,
    CodingInterviewStartResponse,
    # Submit answer responses
    HRSubmitAnswerResponse,
    TechnicalSubmitAnswerResponse,
    STARSubmitAnswerResponse,
    # Next question responses
    HRNextQuestionResponse,
    TechnicalNextQuestionResponse,
    STARNextQuestionResponse,
    CodingNextQuestionResponse,
    # End interview responses
    InterviewEndResponse,
    # Code run response
    CodeRunResponse,
    # Speech responses
    SpeechToTextResponse,
    # Feedback responses
    HRFeedbackResponse,
    TechnicalFeedbackResponse,
    STARFeedbackResponse,
    # Summary and results
    TechnicalSummaryResponse,
    CodingResultItem,
    CodingResultsResponse,
    # Common interview responses
    RolesResponse,
    ExperienceLevelsResponse,
    SessionQuestionsResponse,
    QuestionResponse,
    NextQuestionResponse
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
    "ResumeAnalysisResponse",
    "ResumeUploadResponse",
    "ExperienceUpdateResponse",
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
    "TechnicalInterviewStartRequest",
    "TechnicalInterviewStartResponse",
    "HRInterviewStartResponse",
    "STARInterviewStartResponse",
    "CodingQuestion",
    "CodingInterviewStartResponse",
    # Submit answer responses
    "HRSubmitAnswerResponse",
    "TechnicalSubmitAnswerResponse",
    "STARSubmitAnswerResponse",
    # Next question responses
    "HRNextQuestionResponse",
    "TechnicalNextQuestionResponse",
    "STARNextQuestionResponse",
    "CodingNextQuestionResponse",
    # End interview responses
    "InterviewEndResponse",
    # Code run response
    "CodeRunResponse",
    # Speech responses
    "SpeechToTextResponse",
    # Feedback responses
    "HRFeedbackResponse",
    "TechnicalFeedbackResponse",
    "STARFeedbackResponse",
    # Summary and results
    "TechnicalSummaryResponse",
    "CodingResultItem",
    "CodingResultsResponse",
    # Common interview responses
    "RolesResponse",
    "ExperienceLevelsResponse",
    "SessionQuestionsResponse",
    "QuestionResponse",
    "NextQuestionResponse",
    # Dashboard schemas
    "InterviewSummary",
    "SkillAnalysis",
    "TrendDataPoint",
    "PerformanceDashboardResponse",
    "TrendsDashboardResponse"
]

