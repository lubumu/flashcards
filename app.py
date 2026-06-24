"""Vercel Flask entrypoint.

This module exposes the Flask application as `app` from `flashcard_web.py`
so platforms that expect a default `app.py` entrypoint can load it.
"""

from flashcard_web import app
