"""AI safety validation and response filtering."""
import re
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# Forbidden phrases that indicate dangerous advice
FORBIDDEN_PHRASES = [
    # Dangerous repair suggestions
    r"you can (safely|easily|just) (repair|fix|replace|remove|disconnect)",
    r"no need to (consult|take it to|visit) a (mechanic|professional|dealer)",
    r"don't worry about.*safety",
    r"perfectly safe to (drive|repair|do it yourself)",
    
    # Suggesting dangerous actions
    r"(never|don't) need professional help",
    r"just (remove|disconnect|bypass)",
    r"ignore (the|that).*(warning|light|indicator)",
    r"(driving|riding) (is|was) fine",
    
    # Promising dangerous outcomes  
    r"guaranteed.*safe",
    r"nothing.*wrong.*keep driving",
    r"(no|not).*(danger|risk|problem).*(keep|continue).*driving",
    
    # Overly confident diagnoses
    r"definitely.*broken",
    r"certainly.*repair",
    r"always.*cause",
]

# Compile regex patterns
FORBIDDEN_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PHRASES]

# Safety disclaimer
SAFETY_DISCLAIMER = """

---

⚠️ **Important Safety Notice:**
- This is general information only, not a professional diagnosis
- Always consult a certified mechanic for vehicle repairs
- If you suspect a safety issue, stop driving immediately
- Your safety is the top priority - when in doubt, seek professional help
"""


def validate_response(response: str) -> tuple[bool, Optional[str]]:
    """
    Validate AI response for dangerous content.
    
    Args:
        response: The AI-generated response
        
    Returns:
        Tuple of (is_safe, warning_message)
        - is_safe: False if dangerous content detected
        - warning_message: Warning message if unsafe
    """
    for pattern in FORBIDDEN_PATTERNS:
        match = pattern.search(response)
        if match:
            logger.warning(f"Potentially dangerous content detected: {match.group()}")
            return False, f"Response contains potentially unsafe content near: '{match.group()}'"
    
    return True, None


def append_disclaimer(response: str) -> str:
    """
    Append safety disclaimer to response.
    
    Args:
        response: The AI-generated response
        
    Returns:
        Response with appended disclaimer
    """
    if SAFETY_DISCLAIMER in response:
        return response  # Already has disclaimer
    
    return response + SAFETY_DISCLAIMER


def sanitize_response(response: str) -> str:
    """
    Sanitize AI response by validating and adding disclaimer.
    
    Args:
        response: The AI-generated response
        
    Returns:
        Sanitized response with disclaimer
    """
    is_safe, warning = validate_response(response)
    
    if not is_safe:
        logger.warning(f"Unsafe AI response detected: {warning}")
        # Don't include unsafe content, replace with safe message
        return (
            "I apologize, but I can't provide information that might lead to unsafe repairs. "
            "Please consult a certified mechanic for any vehicle repairs or diagnostics. "
            "Your safety is important to us."
        ) + SAFETY_DISCLAIMER
    
    return append_disclaimer(response)


def check_for_forbidden_content(text: str) -> List[str]:
    """
    Check text for any forbidden content.
    
    Args:
        text: Text to check
        
    Returns:
        List of matched forbidden phrases
    """
    matches = []
    for pattern in FORBIDDEN_PATTERNS:
        match = pattern.search(text)
        if match:
            matches.append(match.group())
    return matches


def is_response_safe(response: str) -> bool:
    """
    Quick check if response is safe (no need for detailed validation).
    
    Args:
        response: The AI-generated response
        
    Returns:
        True if response appears safe
    """
    is_safe, _ = validate_response(response)
    return is_safe
