import logging
from typing import Optional, Any
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Lazy import tracking
OPENAI_AVAILABLE = False
OpenAI = None
ChatOpenAI = None

def _try_import_openai():
    global OPENAI_AVAILABLE, OpenAI
    if OPENAI_AVAILABLE:
        return True
    try:
        from openai import OpenAI
        OPENAI_AVAILABLE = True
        return True
    except ImportError:
        OPENAI_AVAILABLE = False
        return False

def _try_import_langchain():
    global ChatOpenAI
    try:
        from langchain_openai import ChatOpenAI
        return True
    except ImportError:
        return False

def get_api_key_for_type(interview_type: str) -> Optional[str]:
    """
    Get the specific API key for the given interview type.
    Falls back to the main OPENAI_API_KEY logic if specific key is not set,
    but strictly prioritizes specific keys for isolation.
    """
    interview_type = interview_type.lower()
    
    if "tech" in interview_type:
        return settings.openai_tech_api_key or settings.openai_api_key
    elif "hr" in interview_type:
        return settings.openai_hr_api_key or settings.openai_api_key
    elif "star" in interview_type:
        return settings.openai_star_api_key or settings.openai_api_key
    elif "coding" in interview_type:
        return settings.openai_coding_api_key or settings.openai_api_key
    else:
        # Default fallback
        return settings.openai_api_key

def get_openai_client(interview_type: str = "technical") -> Optional[Any]:
    """
    Get an OpenAI client initialized with the correct key for the interview type.
    """
    _try_import_openai()
    if not OPENAI_AVAILABLE or OpenAI is None:
        logger.warning("OpenAI library not installed or import failed.")
        return None
        
    api_key = get_api_key_for_type(interview_type)
    
    if not api_key:
        logger.error(f"No API key found for interview type: {interview_type}")
        return None
        
    try:
        return OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client for {interview_type}: {e}")
        return None

def get_langchain_client(interview_type: str = "technical", temperature: float = 0.7) -> Optional[Any]:
    """
    Get a LangChain ChatOpenAI client initialized with the correct key.
    """
    if not _try_import_langchain():
        logger.warning("LangChain OpenAI library not installed.")
        return None
        
    api_key = get_api_key_for_type(interview_type)
        
    if not api_key:
        logger.error(f"No API key found for interview type: {interview_type}")
        return None
        
    try:
        # Import here to avoid circular imports or issues if module missing
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=temperature,
            openai_api_key=api_key
        )
    except Exception as e:
        logger.error(f"Failed to initialize LangChain client for {interview_type}: {e}")
        return None
