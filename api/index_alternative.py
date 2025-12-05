"""
Alternative handler approach - testing if Vercel supports ASGI apps
when exported differently
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app

# Try exporting as a tuple or dict that Vercel might recognize
# This is experimental
handler = (app,)

