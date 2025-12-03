"""
Utility functions for common operations
"""

from .exceptions import (
    AppException,
    ValidationError,
    NotFoundError,
    DatabaseError
)

from .database import (
    get_user_profile,
    get_interview_session,
    get_question_by_number,
    get_all_answers_for_session,
    batch_insert_questions
)

from .datetime_utils import (
    parse_datetime,
    format_datetime,
    get_current_timestamp
)

from .file_utils import (
    validate_file_type,
    save_temp_file,
    cleanup_temp_file,
    extract_file_extension
)

from .rate_limiter import (
    RateLimiter,
    get_rate_limiter,
    check_rate_limit,
    rate_limit_by_user_id,
    check_session_rate_limit,
    rate_limit_by_session_id
)

from .request_validator import (
    validate_request_size,
    MAX_REQUEST_SIZE
)

__all__ = [
    # Exceptions
    "AppException",
    "ValidationError",
    "NotFoundError",
    "DatabaseError",
    # Database utilities
    "get_user_profile",
    "get_interview_session",
    "get_question_by_number",
    "get_all_answers_for_session",
    "batch_insert_questions",
    # Datetime utilities
    "parse_datetime",
    "format_datetime",
    "get_current_timestamp",
    # File utilities
    "validate_file_type",
    "save_temp_file",
    "cleanup_temp_file",
    "extract_file_extension",
    # Rate limiter
    "RateLimiter",
    "get_rate_limiter",
    "check_rate_limit",
    "rate_limit_by_user_id",
    "check_session_rate_limit",
    "rate_limit_by_session_id",
    # Request validator
    "validate_request_size",
    "MAX_REQUEST_SIZE"
]

