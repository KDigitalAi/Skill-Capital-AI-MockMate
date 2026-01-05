"""
Speech-related endpoints for text-to-speech and speech-to-text functionality
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Body
from fastapi import Request
from fastapi.responses import StreamingResponse, Response
from supabase import Client
from app.db.client import get_supabase_client
from app.utils.openai_factory import get_openai_client
from app.utils.request_validator import validate_request_size
from app.schemas.interview import SpeechToTextResponse
from typing import Dict, Any
import logging
import tempfile
import os
import io
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(tags=["speech"])

def get_interview_type_from_referer(request: Request) -> str:
    """
    Determine interview type based on the Referer header logic.
    Priority:
    1. Check Referer header for specific pages
    2. Default to 'technical'
    """
    referer = request.headers.get("referer", "").lower()
    
    if "star-interview" in referer:
        return "star"
    elif "hr-interview" in referer:
        return "hr"
    elif "coding-interview" in referer:
        return "coding" 
    else:
        return "technical"

@router.post("/speech-to-text", response_model=SpeechToTextResponse)
async def speech_to_text(
    http_request: Request,
    audio: UploadFile = File(...),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Convert speech audio to text using OpenAI Whisper
    Includes safety checks for silent audio and hallucination filtering.
    """
    try:
        # Determine interview type for API key selection
        interview_type = get_interview_type_from_referer(http_request)
        client = get_openai_client(interview_type)
        
        # Check if OpenAI is available
        if client is None:
            raise HTTPException(status_code=503, detail=f"Speech-to-text service is not available for {interview_type}. OpenAI API key is required.")
        
        # Read audio content into memory
        content = await audio.read()
        file_size = len(content)
        
        # 1. AUDIO SANITY CHECK (PRE-WHISPER)
        # Verify file size - silent/empty blobs are often very small (< 1KB)
        # A typical 1-second WebM opus audio is usually > 2-3KB
        if file_size < 1024:  # 1KB threshold
            logger.warning(f"[SPEECH] Silent audio detected (size: {file_size} bytes). Skipping Whisper.")
            return {"text": "No Answer", "language": "en", "is_silent": True}
        
        # Use tempfile (has filesystem access)
        file_extension = os.path.splitext(audio.filename)[1] if audio.filename else ".webm"
        tmp_file_path = None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            # Transcribe using OpenAI Whisper
            try:
                with open(tmp_file_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="en",
                        temperature=0  # Use deterministic sampling
                    )
                text = transcript.text
                
            except Exception as whisper_error:
                logger.error(f"[SPEECH] Whisper API error: {str(whisper_error)}")
                # Fail safely to "No Answer" instead of crashing
                return {"text": "No Answer", "language": "en", "is_silent": True}
            
            # 2. WHISPER OUTPUT SANITIZATION (POST-WHISPER)
            if not text:
                return {"text": "No Answer", "language": "en", "is_silent": True}
                
            # Normalize text for checking
            normalized_text = text.strip().lower()
            
            # Known Whisper hallucinations list
            hallucinations = [
                "thank you", "thanks", "thank you.", "thanks.", 
                "you", "you.", "bye", "bye.",
                "subtitles by", "subtitles by...",
                "(silence)", "[silence]",
                "copyright", "copyright...",
                "continue", "continue.",
                "amara.org"
            ]
            
            # Check for exact matches or very short garbage
            is_hallucination = False
            
            # Check if text is in known hallucinations list
            if any(h in normalized_text for h in hallucinations) and len(normalized_text.split()) <= 5:
                is_hallucination = True
                
            # Check length - extremly short answers (1 word) that aren't Yes/No are suspicious
            word_count = len(normalized_text.split())
            if word_count < 2 and normalized_text not in ["yes", "no", "yes.", "no.", "yeah", "nope"]:
                # Be careful with valid short answers, but for interview context, single words like "the" or "a" are noise
                if len(normalized_text) < 4: # Very short single words
                    is_hallucination = True
            
            if is_hallucination:
                logger.warning(f"[SPEECH] Hallucination detected: '{text}'. Returning 'No Answer'.")
                return {"text": "No Answer", "language": "en", "is_silent": True}

            return {"text": text.strip(), "language": "en", "is_silent": False}
            
        finally:
            # Clean up temporary file
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except Exception as e:
                    logger.warning(f"[SPEECH][SPEECH-TO-TEXT] Could not delete temp file: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error converting speech to text: {str(e)}")


# OPTIONS endpoints removed - CORS is handled by FastAPI CORS middleware in app/main.py


@router.post("/text-to-speech", responses={200: {"content": {"audio/mpeg": {}}}})
async def text_to_speech(
    http_request: Request,
    request_body: Dict[str, Any] = Body(...),
    supabase: Client = Depends(get_supabase_client),
    _: None = Depends(validate_request_size)
):
    """
    Convert text to speech using OpenAI TTS
    Accepts: {"text": "question text"}
    Returns audio file as streaming response
    """
    try:
        text = request_body.get("text", "")
        
        # Determine interview type for API key selection
        interview_type = get_interview_type_from_referer(http_request)
        client = get_openai_client(interview_type)
        
        # Check if OpenAI is available
        if client is None:
            logger.error(f"[SPEECH][TEXT-TO-SPEECH] TTS service unavailable: OpenAI client not initialized for {interview_type}")
            raise HTTPException(
                status_code=503, 
                detail=f"Text-to-speech service is not available for {interview_type}. OpenAI API key is required."
            )
        
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="text parameter is required and cannot be empty")
        
        # Truncate text to reasonable length (OpenAI TTS limit is 4096 chars, but we'll use 2000 for safety)
        text_to_speak = text.strip()[:2000]
        logger.info(f"[SPEECH][TEXT-TO-SPEECH] Generating TTS audio for text (length: {len(text_to_speak)} chars) using {interview_type} key")
        
        # Generate speech using OpenAI TTS
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
                input=text_to_speak
            )
            
            # Get audio data
            audio_data = response.content
            
            if not audio_data or len(audio_data) == 0:
                logger.error("[SPEECH][TEXT-TO-SPEECH] TTS returned empty audio data")
                raise HTTPException(status_code=500, detail="TTS service returned empty audio data")
            
            logger.info(f"[SPEECH][TEXT-TO-SPEECH] TTS generated audio successfully (size: {len(audio_data)} bytes)")
            
            # Return audio as streaming response with proper CORS headers
            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=speech.mp3",
                    "Content-Type": "audio/mpeg",
                    "Content-Length": str(len(audio_data)),
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Accept-Ranges": "bytes"
                }
            )
        except Exception as tts_error:
            logger.error(f"[SPEECH][TEXT-TO-SPEECH] OpenAI TTS API error: {str(tts_error)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate speech: {str(tts_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SPEECH][TEXT-TO-SPEECH] Unexpected error in text_to_speech: {str(e)}")
        import traceback
        logger.error(f"[SPEECH][TEXT-TO-SPEECH] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error converting text to speech: {str(e)}")



@router.get("/text-to-speech", responses={200: {"content": {"audio/mpeg": {}}}})
async def text_to_speech_get(
    request: Request,
    text: str = Query(..., description="Text to convert to speech")
):
    """
    Convert text to speech using OpenAI TTS (GET endpoint for URL-based access)
    Returns audio file as streaming response
    """
    try:
        # Determine interview type for API key selection
        interview_type = get_interview_type_from_referer(request)
        client = get_openai_client(interview_type)

        # Check if OpenAI is available
        if client is None:
            logger.error(f"[SPEECH][TEXT-TO-SPEECH] TTS service unavailable: OpenAI client not initialized for {interview_type}")
            raise HTTPException(
                status_code=503, 
                detail=f"Text-to-speech service is not available for {interview_type}. OpenAI API key is required."
            )
        
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="text parameter is required and cannot be empty")
        
        # Decode URL-encoded text
        import urllib.parse
        decoded_text = urllib.parse.unquote(text).strip()
        
        # Validate text length (max 500 characters)
        if len(decoded_text) > 500:
            raise HTTPException(
                status_code=400, 
                detail=f"text parameter must be 500 characters or less. Received {len(decoded_text)} characters."
            )
        
        # Truncate to reasonable length (OpenAI TTS limit is 4096 chars, but we'll use 2000 for safety)
        text_to_speak = decoded_text[:2000]
        logger.info(f"[SPEECH][TEXT-TO-SPEECH] Generating TTS audio via GET (length: {len(text_to_speak)} chars) using {interview_type} key")
        
        # Generate speech using OpenAI TTS
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text_to_speak
            )
            
            audio_data = response.content
            
            if not audio_data or len(audio_data) == 0:
                logger.error("[SPEECH][TEXT-TO-SPEECH] TTS returned empty audio data")
                raise HTTPException(status_code=500, detail="TTS service returned empty audio data")
            
            logger.info(f"[SPEECH][TEXT-TO-SPEECH] TTS generated audio successfully via GET (size: {len(audio_data)} bytes)")
            
            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=speech.mp3",
                    "Content-Type": "audio/mpeg",
                    "Content-Length": str(len(audio_data)),
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Accept-Ranges": "bytes"
                }
            )
        except Exception as tts_error:
            logger.error(f"[SPEECH][TEXT-TO-SPEECH] OpenAI TTS API error (GET): {str(tts_error)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate speech: {str(tts_error)}"
            )
        
    except Exception as e:
        logger.error(f"[SPEECH][TEXT-TO-SPEECH] Unexpected error in text_to_speech_get: {str(e)}")
        import traceback
        logger.error(f"[SPEECH][TEXT-TO-SPEECH] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error converting text to speech: {str(e)}")


@router.post("/generate-audio", responses={200: {"content": {"audio/mpeg": {}}}})
async def generate_audio(
    http_request: Request,
    request_body: Dict[str, Any] = Body(...),
    supabase: Client = Depends(get_supabase_client),
    _: None = Depends(validate_request_size)
):
    """
    Generate audio from text (Backward compatibility wrapper for text-to-speech)
    Required to support existing frontend implementation.
    DELEGATES to text_to_speech implementation.
    """
    try:
        # Validate request body first
        if not request_body or "text" not in request_body:
            raise HTTPException(status_code=400, detail="text parameter is required")
            
        # Call the implementation directly
        # Note: We pass the exact same arguments to ensure identical behavior
        return await text_to_speech(http_request, request_body, supabase, _)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SPEECH] Error in generate_audio wrapper: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


