"""
User profile schemas
Pydantic models for request/response validation
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserProfileCreate(BaseModel):
    """
    Schema for creating a user profile
    Time Complexity: O(1) - Model validation
    Space Complexity: O(1) - Constant space
    """
    user_id: str
    name: Optional[str] = None
    email: EmailStr
    skills: Optional[List[str]] = []
    experience_level: Optional[str] = None
    resume_url: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """
    Schema for updating a user profile
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    name: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_level: Optional[str] = None
    resume_url: Optional[str] = None


class UserProfileResponse(BaseModel):
    """
    Schema for user profile response
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    id: str
    user_id: str
    name: Optional[str] = None
    email: str
    skills: Optional[List[str]] = []  # Default to empty list if null from DB
    experience_level: Optional[str] = None
    resume_url: Optional[str] = None
    access_role: Optional[str] = "Student"  # Default to "Student"
    created_at: Optional[datetime] = None  # Make optional in case of missing data
    updated_at: Optional[datetime] = None  # Make optional in case of missing data
    
    class Config:
        """Pydantic configuration"""
        # Allow population by field name or alias
        populate_by_name = True
        # Validate assignment
        validate_assignment = True
        # Allow extra fields from database that aren't in schema
        extra = "ignore"



