"""API routers for modular endpoint organization.

This package contains FastAPI routers for the API server organized by functionality.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

from .health import router as health_router
from .scores import router as scores_router
from .analysis import router as analysis_router
from .criteria import router as criteria_router
from .admin import router as admin_router

__all__ = [
    "health_router",
    "scores_router",
    "analysis_router",
    "criteria_router",
    "admin_router",
]

# Made with Bob
