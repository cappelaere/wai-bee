# API Refactoring Guide - Integrating Modular Routers

This guide provides step-by-step instructions for integrating the new modular router structure into the existing `api.py` and applying the same pattern to `chat_api.py`.

## Overview

The refactoring splits large monolithic API files into focused, maintainable router modules:

- **Before:** `api.py` (1426 lines), `chat_api.py` (1139 lines)
- **After:** Multiple focused routers (50-300 lines each)

## Step 1: Update `bee_agents/api.py`

### 1.1 Add Router Imports

Add these imports after the existing imports (around line 44):

```python
# Import modular routers
from .api_routers import (
    health_router,
    scores_router,
    analysis_router,
    criteria_router,
    admin_router
)
```

### 1.2 Remove Duplicate Endpoints

The following endpoints are now in routers and should be **removed** from `api.py`:

**From health_router:**
- `GET /` (lines ~232-245)
- `GET /health` (if exists)

**From scores_router:**
- `GET /score`
- `GET /top_scores`
- `GET /statistics`

**From analysis_router:**
- `GET /application`
- `GET /academic`
- `GET /essay`
- `GET /essay/{essay_number}`
- `GET /recommendation`
- `GET /recommendation/{rec_number}`

**From criteria_router:**
- `GET /criteria`
- `GET /criteria/{scholarship}/{filename}`

**From admin_router:**
- `GET /admin/{scholarship}/weights`
- `PUT /admin/{scholarship}/weights`
- `GET /admin/{scholarship}/criteria/{agent_name}`
- `PUT /admin/{scholarship}/criteria/{agent_name}`
- `POST /admin/{scholarship}/criteria/{agent_name}/regenerate`

### 1.3 Include Routers in App

Add after the CORS middleware setup (around line 145):

```python
# Include modular routers
app.include_router(health_router)
app.include_router(scores_router)
app.include_router(analysis_router)
app.include_router(criteria_router)
app.include_router(admin_router)
```

### 1.4 Keep These Functions (Shared Utilities)

These functions should **remain** in `api.py` as they're used by routers:

```python
def load_available_scholarships() -> List[str]:
    """Load available scholarships from config/users.json."""
    # Keep this function

def get_scholarship_config_path(scholarship_name: str) -> Path:
    """Get path to canonical config.yml for a scholarship."""
    # Keep this function

def load_scholarship_config(scholarship_name: str) -> Dict[str, Any]:
    """Load canonical scholarship config."""
    # Keep this function

def initialize_services(base_output_dir: str = "outputs"):
    """Initialize data services for all available scholarships."""
    # Keep this function

def get_data_service(scholarship: str) -> DataService:
    """Get the data service for a specific scholarship."""
    # Keep this function
```

### 1.5 Keep These Endpoints (Not Yet Modularized)

These endpoints should remain in `api.py` for now:

- `GET /favicon.ico`
- `GET /scholarship` - Get scholarship info
- `GET /openapi.yml` - OpenAPI spec
- `GET /openapi.json` - OpenAPI spec
- `GET /agents` - List agents
- `GET /agents/{scholarship}/{agent_name}` - Get agent config

## Step 2: Create Chat Routers for `chat_api.py`

### 2.1 Create Router Directory Structure

```
bee_agents/
├── api_api_routers/         # API server routers
│   ├── __init__.py
│   ├── health.py
│   ├── scores.py
│   ├── analysis.py
│   ├── criteria.py
│   ├── admin.py
│   └── README.md
└── chat_api_routers/        # Chat server routers
├── __init__.py
├── auth.py          # Login/logout endpoints
├── chat.py          # WebSocket chat endpoint
├── scholarship.py   # Scholarship selection
└── README.md
```

### 2.2 Create `bee_agents/chat_api_routers/__init__.py`

```python
"""Chat API routers for modular endpoint organization.

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
```

### 2.3 Create `bee_agents/chat_api_routers/auth.py`

```python
"""Authentication endpoints for chat interface.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from ..auth import (
    LoginRequest,
    LoginResponse,
    create_token_with_context,
    verify_credentials,
    revoke_token
)

router = APIRouter(tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.get("/login", response_class=HTMLResponse)
async def get_login_page():
    """Serve the login page."""
    template_path = Path(__file__).parent.parent / "templates" / "login.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"Login template not found: {template_path}")
        raise HTTPException(status_code=500, detail="Login template not found")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Handle login requests with scholarship context."""
    if not verify_credentials(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token_response = create_token_with_context(request.username)
    logger.info(
        f"User logged in: {request.username}",
        extra={
            "username": request.username,
            "role": token_response["role"],
            "scholarships": token_response["scholarships"]
        }
    )
    
    return LoginResponse(**token_response)


@router.post("/logout")
async def logout(token: str):
    """Handle logout requests."""
    success = revoke_token(token)
    if success:
        return {"message": "Logged out successfully"}
    return {"message": "Token not found or already expired"}
```

### 2.4 Create `bee_agents/chat_api_routers/scholarship.py`

```python
"""Scholarship selection endpoints.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Cookie
from fastapi.responses import HTMLResponse
from ..auth import verify_token_with_context, active_tokens
from ..middleware import ScholarshipAccessMiddleware

router = APIRouter(tags=["Scholarship"])
logger = logging.getLogger(__name__)


@router.get("/select-scholarship", response_class=HTMLResponse)
async def get_scholarship_selection_page():
    """Serve the scholarship selection page."""
    template_path = Path(__file__).parent.parent / "templates" / "select_scholarship.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"Scholarship selection template not found: {template_path}")
        raise HTTPException(status_code=500, detail="Template not found")


@router.post("/api/user/select-scholarship")
async def select_scholarship(
    request: dict,
    auth_token: Optional[str] = Cookie(None)
):
    """Store the user's selected scholarship in their session."""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    scholarship = request.get("scholarship")
    if not scholarship:
        raise HTTPException(status_code=400, detail="Scholarship not provided")
    
    # Verify user has access to this scholarship
    middleware = ScholarshipAccessMiddleware(token_data)
    if not middleware.can_access_scholarship(scholarship):
        raise HTTPException(status_code=403, detail="Access denied to this scholarship")
    
    # Store selected scholarship in token data
    if auth_token in active_tokens:
        active_tokens[auth_token]["selected_scholarship"] = scholarship
        logger.info(
            f"User selected scholarship: {token_data['username']} -> {scholarship}",
            extra={
                "username": token_data["username"],
                "scholarship": scholarship
            }
        )
    
    return {"message": "Scholarship selected successfully", "scholarship": scholarship}
```

### 2.5 Create `bee_agents/chat_api_routers/chat.py`

```python
"""WebSocket chat endpoint.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..chat_agents import MultiAgentOrchestrator
from ..chat_agents_single import SingleAgentHandler

router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat communication."""
    await websocket.accept()
    
    try:
        # Get agent handler from app state
        # This will be set during app initialization
        agent_handler = websocket.app.state.agent_handler
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Process message with agent handler
            # Implementation depends on agent_handler type
            if isinstance(agent_handler, MultiAgentOrchestrator):
                response = await agent_handler.process_message(data)
            else:
                response = await agent_handler.process_message(data)
            
            # Send response back to client
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
```

### 2.6 Update `chat_api.py` to Use Routers

Add after imports:

```python
# Import chat routers
from .chat_routers import (
    auth_router,
    chat_router,
    scholarship_router
)
```

Add after CORS middleware:

```python
# Include chat routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(scholarship_router)
```

Remove duplicate endpoints that are now in routers.

## Step 3: Testing the Refactored API

### 3.1 Test Health Endpoints

```bash
curl http://localhost:8200/
curl http://localhost:8200/health
```

### 3.2 Test Score Endpoints

```bash
curl "http://localhost:8200/score?scholarship=Delaney_Wings&wai_number=75179"
curl "http://localhost:8200/top_scores?scholarship=Delaney_Wings&limit=10"
curl "http://localhost:8200/statistics?scholarship=Delaney_Wings"
```

### 3.3 Test Analysis Endpoints

```bash
curl "http://localhost:8200/application?scholarship=Delaney_Wings&wai_number=75179"
curl "http://localhost:8200/academic?scholarship=Delaney_Wings&wai_number=75179"
```

### 3.4 Test Criteria Endpoints

```bash
curl "http://localhost:8200/criteria?scholarship=Delaney_Wings"
curl "http://localhost:8200/criteria/Delaney_Wings/application_criteria.txt"
```

## Step 4: Update Tests

### 4.1 Update `tests/conftest.py`

No changes needed - the test client will automatically use the new routers.

### 4.2 Add Router-Specific Tests

Create new test files:

```
tests/
├── test_api_routers/
│   ├── __init__.py
│   ├── test_health_router.py
│   ├── test_scores_router.py
│   ├── test_analysis_router.py
│   ├── test_criteria_router.py
│   └── test_admin_router.py
```

Example `test_health_router.py`:

```python
"""Tests for health router endpoints."""

import pytest


def test_root_endpoint(test_client):
    """Test the root endpoint returns API information."""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "status" in data


def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
```

## Step 5: Update Documentation

### 5.1 Update README.md

Add section about modular architecture:

```markdown
## API Architecture

The API uses a modular router architecture for better maintainability:

- **Health Router**: Health checks and status
- **Scores Router**: Score and statistics endpoints
- **Analysis Router**: Application analysis endpoints
- **Criteria Router**: Criteria management
- **Admin Router**: Administrative configuration

See `bee_agents/api_api_routers/README.md` for details.
```

### 5.2 Update OpenAPI Documentation

The OpenAPI documentation will automatically reflect the new router structure with proper tags.

## Benefits of This Refactoring

1. **Reduced Complexity**: Each router file is under 300 lines
2. **Better Organization**: Related endpoints grouped together
3. **Easier Testing**: Can test routers independently
4. **Improved Maintainability**: Easy to locate and update code
5. **Team Collaboration**: Multiple developers can work on different routers
6. **Scalability**: Easy to add new routers without bloating main file

## Rollback Plan

If issues arise, you can temporarily disable routers:

```python
# Comment out router includes
# app.include_router(health_router)
# app.include_router(scores_router)
# etc.

# Keep old endpoints active until migration is complete
```

## Author

Pat G Cappelaere, IBM Federal Consulting

## Version

1.0.0 - Initial refactoring guide (2025-12-16)