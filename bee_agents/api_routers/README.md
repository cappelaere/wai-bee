# API Routers - Modular Endpoint Organization

This directory contains FastAPI routers for the API server organized by functionality for better maintainability and code organization.

## Structure

```
api_routers/
├── __init__.py          # Router exports
├── health.py            # Health check and status endpoints
├── scores.py            # Score and statistics endpoints
├── analysis.py          # Analysis endpoints (application, academic, essay, recommendation)
├── criteria.py          # Criteria management endpoints
├── admin.py             # Admin configuration endpoints
└── README.md            # This file
```

## Routers

### Health Router (`health.py`)
- `GET /` - Root endpoint with API info
- `GET /health` - Health check for monitoring

### Scores Router (`scores.py`)
- `GET /score` - Get score for specific application
- `GET /top_scores` - Get top scoring applications
- `GET /statistics` - Get aggregated statistics

### Analysis Router (`analysis.py`)
- `GET /application` - Get application analysis
- `GET /academic` - Get academic analysis
- `GET /essay` - Get combined essay analysis
- `GET /essay/{essay_number}` - Get specific essay analysis
- `GET /recommendation` - Get combined recommendation analysis
- `GET /recommendation/{rec_number}` - Get specific recommendation analysis

### Criteria Router (`criteria.py`)
- `GET /criteria` - List all criteria files
- `GET /criteria/{scholarship}/{filename}` - Download specific criteria file

### Admin Router (`admin.py`)
- `GET /admin/{scholarship}/weights` - Get scoring weights
- `PUT /admin/{scholarship}/weights` - Update scoring weights
- `GET /admin/{scholarship}/criteria/{agent_name}` - Get agent criteria
- `PUT /admin/{scholarship}/criteria/{agent_name}` - Update agent criteria
- `POST /admin/{scholarship}/criteria/{agent_name}/regenerate` - Regenerate criteria with LLM

## Usage in Main API

The routers are imported and included in the main FastAPI app:

```python
from bee_agents.api_routers import (
    health_router,
    scores_router,
    analysis_router,
    criteria_router,
    admin_router
)

app = FastAPI(...)

# Include routers
app.include_router(health_router)
app.include_router(scores_router)
app.include_router(analysis_router)
app.include_router(criteria_router)
app.include_router(admin_router)
```

## Benefits

1. **Modularity**: Each router focuses on a specific domain
2. **Maintainability**: Easier to locate and update endpoints
3. **Testability**: Can test routers independently
4. **Scalability**: Easy to add new routers without bloating main file
5. **Team Collaboration**: Multiple developers can work on different routers

## Adding New Routers

1. Create new router file in `api_routers/` directory
2. Define router with `APIRouter(tags=["YourTag"])`
3. Add endpoints using `@router.get()`, `@router.post()`, etc.
4. Export router in `__init__.py`
5. Include router in main `api.py`

Example:

```python
# api_routers/new_feature.py
from fastapi import APIRouter

router = APIRouter(tags=["NewFeature"])

@router.get("/new-endpoint")
async def new_endpoint():
    return {"message": "Hello from new router"}
```

```python
# api_routers/__init__.py
from .new_feature import router as new_feature_router

__all__ = [..., "new_feature_router"]
```

```python
# api.py
from bee_agents.api_routers import new_feature_router

app.include_router(new_feature_router)
```

## Author

Pat G Cappelaere, IBM Federal Consulting

## Version

1.0.0 - Initial modular structure (2025-12-16)