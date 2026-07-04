"""Compatibility wrapper for the refactored GUI modules.

Importing `gui` still exposes `main()` for backward compatibility while the
implementation lives in `app.py` and supporting modules.
"""
from .app import main
