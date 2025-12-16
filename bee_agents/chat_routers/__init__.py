"""Chat API routers for modular endpoint organization.

This package contains FastAPI routers for the chat interface organized by functionality.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

from .auth import router as auth_router
from .chat import router as chat_router
from .scholarship import router as scholarship_router

__all__ = [
    "auth_router",
    "chat_router",
    "scholarship_router",
]

# Made with Bob
