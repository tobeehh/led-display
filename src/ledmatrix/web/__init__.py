"""Web interface module.

Provides:
- FastAPI application with REST API
- Authentication and session management
- CSRF protection
- HTML templates and static assets
"""

from .app import create_app, get_app

__all__ = [
    "create_app",
    "get_app",
]
