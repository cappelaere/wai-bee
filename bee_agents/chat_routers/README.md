# Chat API Routers - Modular Endpoint Organization

This directory contains FastAPI routers for the chat interface organized by functionality.

## Structure

```
chat_routers/
├── __init__.py          # Router exports
├── auth.py              # Authentication endpoints (login/logout)
├── scholarship.py       # Scholarship selection endpoints
├── chat.py              # Chat interface and WebSocket endpoints
└── README.md            # This file
```

## Routers

### Auth Router (`auth.py`)
Handles user authentication and session management.

**Endpoints:**
- `GET /login` - Serve login page
- `POST /login` - Handle login with credentials
- `POST /logout` - Handle logout and token revocation

**Features:**
- Multi-tenancy support with scholarship-based access
- Token-based authentication
- Role and permission management

### Scholarship Router (`scholarship.py`)
Manages scholarship selection and access control.

**Endpoints:**
- `GET /select-scholarship` - Serve scholarship selection page
- `POST /api/user/select-scholarship` - Store selected scholarship in session
- `GET /api/user/scholarships` - Get list of accessible scholarships

**Features:**
- Access control validation
- Session management
- User-specific scholarship filtering

### Chat Router (`chat.py`)
Provides the main chat interface and WebSocket communication.

**Endpoints:**
- `GET /` - Serve main chat interface
- `GET /about` - Serve about page
- `GET /examples` - Serve examples page
- `GET /health` - Health check endpoint
- `GET /favicon.ico` - Serve favicon
- `GET /admin/config` - Serve admin configuration page
- `WebSocket /ws` - Real-time chat communication

**Features:**
- WebSocket support for real-time messaging
- Agent handler integration (multi-agent or single-agent)
- Error handling and logging
- Template serving

## Usage in Chat API

The routers are imported and included in the main chat FastAPI app:

```python
from bee_agents.chat_routers import (
    auth_router,
    scholarship_router,
    chat_router
)

app = FastAPI(...)

# Include routers
app.include_router(auth_router)
app.include_router(scholarship_router)
app.include_router(chat_router)
```

## WebSocket Communication

The WebSocket endpoint (`/ws`) handles bidirectional communication:

1. **Client connects** → WebSocket accepts connection
2. **Client sends message** → Router receives JSON data
3. **Agent processes** → Multi-agent or single-agent handler
4. **Agent responds** → Streams response back to client
5. **Connection closes** → Cleanup and logging

### Message Format

**Client to Server:**
```json
{
  "type": "message",
  "content": "User's question",
  "scholarship": "Delaney_Wings",
  "context": {}
}
```

**Server to Client:**
```json
{
  "type": "response",
  "content": "Agent's answer",
  "agent": "application_agent",
  "metadata": {}
}
```

## Benefits

1. **Modularity**: Each router focuses on specific functionality
2. **Maintainability**: Easier to locate and update endpoints
3. **Testability**: Can test routers independently
4. **Scalability**: Easy to add new features
5. **Separation of Concerns**: Auth, chat, and scholarship logic separated

## Integration Steps

### 1. Import Routers in `chat_api.py`

Add after existing imports:

```python
# Import chat routers
from .chat_routers import (
    auth_router,
    scholarship_router,
    chat_router
)
```

### 2. Include Routers in App

Add after CORS middleware setup:

```python
# Include chat routers
app.include_router(auth_router)
app.include_router(scholarship_router)
app.include_router(chat_router)

logger.info("Chat routers integrated successfully")
```

### 3. Remove Duplicate Endpoints

Remove these endpoints from `chat_api.py` (now in routers):

**From auth_router:**
- `GET /login`
- `POST /login`
- `POST /logout`

**From scholarship_router:**
- `GET /select-scholarship`
- `POST /api/user/select-scholarship`

**From chat_router:**
- `GET /` (main chat page)
- `GET /about`
- `GET /examples`
- `GET /health`
- `GET /favicon.ico`
- `GET /admin/config`
- `WebSocket /ws`

### 4. Keep Shared State

Ensure agent handler is accessible to routers:

```python
# In chat_api.py startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize agent handler
    global agent_handler
    agent_handler = MultiAgentOrchestrator() or SingleAgentHandler()
    
    # Make it accessible to routers via app state
    app.state.agent_handler = agent_handler
    
    yield
```

## Testing

### Test Authentication
```bash
# Get login page
curl http://localhost:8100/login

# Login
curl -X POST http://localhost:8100/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"password"}'
```

### Test Scholarship Selection
```bash
# Get scholarships
curl http://localhost:8100/api/user/scholarships \
  --cookie "auth_token=YOUR_TOKEN"

# Select scholarship
curl -X POST http://localhost:8100/api/user/select-scholarship \
  -H "Content-Type: application/json" \
  --cookie "auth_token=YOUR_TOKEN" \
  -d '{"scholarship":"Delaney_Wings"}'
```

### Test Chat Interface
```bash
# Get chat page
curl http://localhost:8100/

# Health check
curl http://localhost:8100/health
```

### Test WebSocket
Use a WebSocket client or browser console:

```javascript
const ws = new WebSocket('ws://localhost:8100/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'message',
    content: 'Hello, agent!',
    scholarship: 'Delaney_Wings'
  }));
};

ws.onmessage = (event) => {
  console.log('Response:', JSON.parse(event.data));
};
```

## Adding New Routers

1. Create new router file in `chat_routers/` directory
2. Define router with `APIRouter(tags=["YourTag"])`
3. Add endpoints using decorators
4. Export router in `__init__.py`
5. Include router in main `chat_api.py`

Example:

```python
# chat_routers/analytics.py
from fastapi import APIRouter

router = APIRouter(tags=["Analytics"])

@router.get("/analytics/usage")
async def get_usage_stats():
    return {"message": "Usage statistics"}
```

## Author

Pat G Cappelaere, IBM Federal Consulting

## Version

1.0.0 - Initial modular structure (2025-12-16)