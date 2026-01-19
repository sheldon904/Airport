"""Vercel serverless function entrypoint."""

import sys
from pathlib import Path

# Add project root to Python path for imports to work
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from services.api.main import app

# Export for Vercel
app = app
