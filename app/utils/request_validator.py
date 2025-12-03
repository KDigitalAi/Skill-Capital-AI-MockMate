"""
Request validation utilities
Includes request body size validation
"""

from fastapi import HTTPException, Request
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Maximum request body size: 2MB
MAX_REQUEST_SIZE = 2 * 1024 * 1024  # 2MB in bytes

async def validate_request_size(request: Request) -> None:
    """
    FastAPI dependency to validate request body size (max 2MB)
    Checks Content-Length header before body is read
    
    Usage:
        @router.post("/endpoint")
        async def my_endpoint(
            request: Request,
            body: Dict = Body(...),
            _: None = Depends(validate_request_size)
        ):
            ...
    """
    # Check Content-Length header if available
    content_length = request.headers.get("content-length")
    
    if content_length:
        try:
            size = int(content_length)
            if size > MAX_REQUEST_SIZE:
                logger.warning(f"[REQUEST-VALIDATOR] Request body size ({size} bytes) exceeds maximum ({MAX_REQUEST_SIZE} bytes)")
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum size is 2MB. Your request is {size / (1024 * 1024):.2f}MB."
                )
        except ValueError:
            # Invalid Content-Length header, skip validation
            logger.debug("[REQUEST-VALIDATOR] Invalid Content-Length header, skipping size check")
            pass
    
    # If Content-Length is not available, we can't check size without reading the body
    # In that case, we'll let FastAPI handle it (it has its own limits)
    # The actual body reading will happen in the endpoint handler

