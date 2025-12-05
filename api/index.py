"""
Vercel serverless function entry point for FastAPI
Multiple approaches to resolve Vercel's handler detection issue.

APPROACH: Try using a minimal BaseHTTPRequestHandler that delegates to FastAPI
"""

import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the FastAPI app
from app.main import app

# APPROACH 1: Simple export - Vercel should auto-detect ASGI apps
# This is the standard way, but Vercel's detection code has a bug
handler = app

# APPROACH 2: Also try exporting as a module-level variable
# Some Vercel configurations might look for this
__all__ = ['handler', 'app']
