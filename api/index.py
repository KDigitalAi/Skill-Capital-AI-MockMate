"""
Vercel serverless function entry point for FastAPI
This file is used by Vercel to handle all API routes as serverless functions
"""

import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the FastAPI app
from app.main import app

# Export handler for Vercel
# Vercel's Python runtime should auto-detect ASGI apps
# The handler should be the ASGI application instance
handler = app

