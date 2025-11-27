"""
Database utility functions for optimized queries
"""

from typing import Optional, List, Dict, Any
from supabase import Client
from datetime import datetime
from app.utils.exceptions import NotFoundError, DatabaseError


def sanitize_user_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize user profile data from database
    Converts None values to appropriate defaults for list/array fields
    Ensures all fields are present with consistent types
    
    Time Complexity: O(1) - Constant time field updates
    Space Complexity: O(1) - In-place updates
    
    Args:
        profile: Raw user profile dictionary from database
        
    Returns:
        Sanitized profile dictionary with consistent field types
    """
    if not profile:
        return profile
    
    # Create a copy to avoid mutating the original
    sanitized = profile.copy()
    
    # Convert None to empty list for array/list fields
    # These fields should always be lists, never None
    list_fields = ['skills', 'projects', 'education', 'experience']
    for field in list_fields:
        if field in sanitized:
            # If field exists but is None, convert to empty list
            if sanitized[field] is None:
                sanitized[field] = []
            # If field is not a list (shouldn't happen, but be safe), convert to list
            elif not isinstance(sanitized[field], list):
                sanitized[field] = []
        else:
            # Field doesn't exist, add it as empty list
            sanitized[field] = []
    
    # Ensure optional string fields are None instead of missing
    # These fields can be None, but should exist in the dict
    optional_string_fields = ['name', 'experience_level', 'resume_url']
    for field in optional_string_fields:
        if field not in sanitized:
            sanitized[field] = None
    
    # Ensure access_role defaults to "Student" if not set or None
    if 'access_role' not in sanitized or not sanitized.get('access_role'):
        sanitized['access_role'] = 'Student'
    
    return sanitized


async def get_user_profile(supabase: Client, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user profile by user_id
    Time Complexity: O(1) - Single indexed query
    Space Complexity: O(1) - Returns single record
    Optimization: Uses indexed query on user_id
    """
    try:
        response = supabase.table("user_profiles").select("*").eq("user_id", user_id).limit(1).execute()
        if response.data and len(response.data) > 0:
            return sanitize_user_profile(response.data[0])
        return None
    except Exception as e:
        raise DatabaseError(f"Error fetching user profile: {str(e)}")


async def get_authenticated_user(supabase: Client, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get authenticated user from user_profiles table
    If user_id is provided, fetch that specific user
    Otherwise, get the first user (for development/testing)
    Time Complexity: O(1) - Single query
    Space Complexity: O(1) - Returns single record
    """
    try:
        if user_id:
            # Get specific user by user_id
            response = supabase.table("user_profiles").select("*").eq("user_id", user_id).limit(1).execute()
            if response.data and len(response.data) > 0:
                return sanitize_user_profile(response.data[0])
        else:
            # Get first user from user_profiles (for development)
            response = supabase.table("user_profiles").select("*").limit(1).execute()
            if response.data and len(response.data) > 0:
                return sanitize_user_profile(response.data[0])
        return None
    except Exception as e:
        raise DatabaseError(f"Error fetching authenticated user: {str(e)}")


async def get_interview_session(supabase: Client, session_id: str) -> Dict[str, Any]:
    """
    Get interview session by session_id
    Time Complexity: O(1) - Single indexed query
    Space Complexity: O(1) - Returns single record
    Optimization: Uses indexed query on session_id
    """
    try:
        response = supabase.table("interview_sessions").select("*").eq("id", session_id).limit(1).execute()
        if not response.data or len(response.data) == 0:
            raise NotFoundError("Interview session", session_id)
        return response.data[0]
    except NotFoundError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error fetching interview session: {str(e)}")


async def get_question_by_number(
    supabase: Client, 
    session_id: str, 
    question_number: int,
    round_table: str = "technical_round"
) -> Optional[Dict[str, Any]]:
    """
    Get question by session_id and question_number from round table
    Time Complexity: O(1) - Single indexed query
    Space Complexity: O(1) - Returns single record
    Optimization: Uses composite index on (session_id, question_number)
    """
    try:
        response = (
            supabase.table(round_table)
            .select("*")
            .eq("session_id", session_id)
            .eq("question_number", question_number)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data and len(response.data) > 0 else None
    except Exception as e:
        raise DatabaseError(f"Error fetching question: {str(e)}")


async def get_all_answers_for_session(
    supabase: Client, 
    session_id: str,
    round_table: str = "technical_round"
) -> List[Dict[str, Any]]:
    """
    Get all answers for a session from round table, ordered by question_number
    Time Complexity: O(n) where n = number of answers
    Space Complexity: O(n) - Returns list of answers
    Optimization: Single query with ordering, avoids N+1 queries
    """
    try:
        response = (
            supabase.table(round_table)
            .select("*")
            .eq("session_id", session_id)
            .order("question_number")
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        raise DatabaseError(f"Error fetching answers: {str(e)}")


async def batch_insert_questions(
    supabase: Client,
    session_id: str,
    questions: List[Dict[str, Any]],
    round_table: str = "technical_round",
    user_id: str = ""
) -> bool:
    """
    Batch insert questions for a session into round table
    Time Complexity: O(n) where n = number of questions
    Space Complexity: O(n) - Stores all questions in memory
    Optimization: Single batch insert instead of multiple individual inserts
    """
    try:
        if not questions:
            return False
        
        # Prepare questions data for round table
        questions_data = []
        for idx, question in enumerate(questions, start=1):
            questions_data.append({
                "user_id": user_id,
                "session_id": session_id,
                "question_number": idx,
                "question_text": question.get("question", ""),
                "question_type": question.get("type", "Technical"),
                "user_answer": ""  # Initialize with empty answer
            })
        
        # Batch insert
        response = supabase.table(round_table).insert(questions_data).execute()
        return response.data is not None and len(response.data) > 0
    except Exception as e:
        raise DatabaseError(f"Error inserting questions: {str(e)}")


async def get_total_questions_count(supabase: Client, session_id: str, round_table: str = "technical_round") -> int:
    """
    Get total questions count for a session from round table
    Time Complexity: O(1) - Count query with index
    Space Complexity: O(1) - Returns integer
    Optimization: Uses COUNT query instead of fetching all records
    """
    try:
        response = (
            supabase.table(round_table)
            .select("id", count="exact")
            .eq("session_id", session_id)
            .execute()
        )
        return response.count if hasattr(response, 'count') else 0
    except Exception as e:
        raise DatabaseError(f"Error counting questions: {str(e)}")

