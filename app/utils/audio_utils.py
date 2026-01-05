
import logging

logger = logging.getLogger(__name__)

def is_hallucination(text: str) -> bool:
    """
    Detect if the transcribed text is a likely hallucination from OpenAI Whisper.
    
    Args:
        text: The transcribed text string
        
    Returns:
        bool: True if it appears to be a hallucination/noise, False otherwise.
    """
    if not text:
        return False
        
    normalized_text = text.strip().lower()
    
    # Remove trailing punctuation for cleaner comparison
    clean_text = normalized_text.rstrip(".,!?")
    
    # Known Whisper hallucinations list (Consolidated)
    hallucinations = [
        "thank you", "thanks", "thank you.", "thanks.", 
        "you", "you.", "bye", "bye.", "goodbye",
        "subtitles by", "subtitles by...",
        "(silence)", "[silence]", "(noise)", "(background noise)",
        "copyright", "copyright...",
        "continue", "continue.",
        "amara.org",
        "thanks for watching", "thanks for watching!",
        "thank you for watching", "thank you for watching!",
        "i love you", "i love you.",
        "ok", "okay", "hello", "hi", "test", "testing"
    ]
    
    # 1. Check for known hallucination phrases in short texts
    # If the text contains one of the phrases AND is very short (<= 5 words), it's likely a hallucination
    if len(normalized_text.split()) <= 5:
        for h in hallucinations:
            # For short words (<= 3 chars) or specific common words, enforce word boundary
            # This prevents "hi" matching in "this", "you" in "young", etc.
            if len(h.split()) == 1 and len(h) <= 4:
                # Check if 'h' is a distinct word in the text (ignoring punctuation logic is tricky, 
                # but we can check if it exists in the split list or use regex)
                # Simple approach: Check if h is in the list of words (stripped of punctuation)
                words = [w.strip(".,!?") for w in normalized_text.split()]
                if h in words:
                    return True
                
                # Also handle cases like "thank you." -> "thank" "you" (stripped)
                # But "hi" might be "hi."
            else:
                # Phrases like "thanks for watching" or longer words "copyright"
                # Substring match is usually safe and desirable
                if h in normalized_text:
                    return True

        
    # 2. Check for repetitive patterns (e.g. "You You You")
    if len(normalized_text) < 10 and normalized_text.count("you") > 1:
        return True
        
    # 3. Check for extremely short answers (1 word) that aren't valid yes/no responses
    word_count = len(normalized_text.split())
    valid_short_answers = ["yes", "no", "yes.", "no.", "yeah", "nope", "yep", "sure"]
    
    if word_count < 2 and normalized_text not in valid_short_answers:
        # Be careful with valid short answers, but for interview context, 
        # single words like "the" or "a" (length < 4) are usually noise
        if len(normalized_text) < 4: 
            return True
            
    return False
