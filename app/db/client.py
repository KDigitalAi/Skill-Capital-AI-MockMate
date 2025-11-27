"""
Supabase database client management
Optimized with singleton pattern to reuse connections
"""

from supabase import create_client, Client
from typing import Optional
from app.config.settings import settings


# Singleton pattern for database client
_supabase_client: Optional[Client] = None
_supabase_anon_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance (service role)
    Uses singleton pattern to reuse connection
    Time Complexity: O(1) - Returns cached instance or creates once
    Space Complexity: O(1) - Single client instance
    Optimization: Singleton pattern prevents multiple client creation
    """
    global _supabase_client
    
    if _supabase_client is None:
        # Validate configuration
        if not settings.supabase_url:
            raise ValueError(
                "SUPABASE_URL environment variable is not set. "
                "Please add it to your .env file: SUPABASE_URL=https://your-project.supabase.co"
            )
        if not settings.supabase_service_key:
            raise ValueError(
                "SUPABASE_SERVICE_KEY environment variable is not set. "
                "Please add it to your .env file. "
                "You can find it in Supabase Dashboard → Settings → API → service_role key"
            )
        
        # Validate URL format
        if not settings.supabase_url.startswith("http"):
            raise ValueError(
                f"Invalid SUPABASE_URL format: {settings.supabase_url}. "
                "URL should start with https://"
            )
        
        try:
            _supabase_client = create_client(
                settings.supabase_url, 
                settings.supabase_service_key
            )
        except Exception as e:
            raise ValueError(
                f"Failed to create Supabase client: {str(e)}. "
                "Please verify your SUPABASE_URL and SUPABASE_SERVICE_KEY are correct."
            ) from e
    
    return _supabase_client


def get_supabase_client_anon() -> Client:
    """
    Get or create Supabase client with anon key (for frontend use)
    Time Complexity: O(1)
    Space Complexity: O(1)
    Optimization: Singleton pattern with separate anon client
    """
    global _supabase_anon_client
    
    if _supabase_anon_client is None:
        # Validate configuration
        if not settings.supabase_url:
            raise ValueError(
                "SUPABASE_URL environment variable is not set. "
                "Please add it to your .env file: SUPABASE_URL=https://your-project.supabase.co"
            )
        if not settings.supabase_key:
            raise ValueError(
                "SUPABASE_KEY environment variable is not set. "
                "Please add it to your .env file. "
                "You can find it in Supabase Dashboard → Settings → API → anon/public key"
            )
        
        # Validate URL format
        if not settings.supabase_url.startswith("http"):
            raise ValueError(
                f"Invalid SUPABASE_URL format: {settings.supabase_url}. "
                "URL should start with https://"
            )
        
        try:
            _supabase_anon_client = create_client(
                settings.supabase_url, 
                settings.supabase_key
            )
        except Exception as e:
            raise ValueError(
                f"Failed to create Supabase anon client: {str(e)}. "
                "Please verify your SUPABASE_URL and SUPABASE_KEY are correct."
            ) from e
    
    return _supabase_anon_client