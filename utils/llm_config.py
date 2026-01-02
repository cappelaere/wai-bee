"""LiteLLM configuration utilities.

This module centralizes LiteLLM log suppression so agents don't repeat the
same boilerplate.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-01-01
Version: 1.0.0
License: MIT
"""

import os

_configured = False


def configure_litellm() -> None:
    """Suppress LiteLLM verbose logging.

    Call once at agent initialization. Safe to call multiple times.
    """
    global _configured
    if _configured:
        return

    os.environ["LITELLM_LOG"] = "ERROR"

    # Import here to avoid circular imports and ensure env is set first
    import litellm
    litellm.suppress_debug_info = True

    _configured = True

