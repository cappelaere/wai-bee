"""
FastAPI server for scholarship chat agent system.

Provides REST and WebSocket endpoints for querying scholarship application data.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..agents.orchestrator import OrchestratorAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Scholarship Chat Agent API",
    description="Conversational interface for querying scholarship application results",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for web interface
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Configuration
OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"
DEFAULT_MODEL = os.getenv('ORCHESTRATOR_MODEL', 'llama3.2:3b')
# Remove 'ollama/' prefix if present
if DEFAULT_MODEL.startswith('ollama/'):
    DEFAULT_MODEL = DEFAULT_MODEL.replace('ollama/', '')

# Session management
sessions: Dict[str, OrchestratorAgent] = {}


# Request/Response Models
class ChatMessage(BaseModel):
    """Chat message request."""
    message: str
    scholarship: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat message response."""
    response: str
    session_id: str
    scholarship: str


class SessionInfo(BaseModel):
    """Session information."""
    session_id: str
    created: bool


# Helper Functions
def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, OrchestratorAgent, bool]:
    """Get existing session or create new one."""
    if session_id and session_id in sessions:
        return session_id, sessions[session_id], False
    
    # Create new session
    new_session_id = session_id or str(uuid4())
    orchestrator = OrchestratorAgent(
        outputs_dir=OUTPUTS_DIR,
        model=DEFAULT_MODEL
    )
    sessions[new_session_id] = orchestrator
    logger.info(f"Created new session: {new_session_id}")
    return new_session_id, orchestrator, True


# REST Endpoints
@app.get("/")
async def root():
    """Root endpoint - serve web interface."""
    index_file = static_dir / "index.html" if static_dir.exists() else None
    if index_file and index_file.exists():
        return FileResponse(index_file)
    return {
        "message": "Scholarship Chat Agent API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "POST /api/chat/message",
            "websocket": "WS /ws/chat/{session_id}",
            "files": "GET /api/files/{scholarship}/{wai}/{filename}",
            "session": "POST /api/session/create"
        }
    }


@app.post("/api/chat/message", response_model=ChatResponse)
async def chat_message(request: ChatMessage):
    """
    Send a chat message and get response.
    
    Args:
        request: Chat message with scholarship and optional session_id
        
    Returns:
        Chat response with session_id
    """
    try:
        session_id, orchestrator, created = get_or_create_session(request.session_id)
        
        # Process message
        response = orchestrator.chat(
            message=request.message,
            scholarship=request.scholarship
        )
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            scholarship=request.scholarship
        )
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/create", response_model=SessionInfo)
async def create_session():
    """Create a new chat session."""
    session_id, _, created = get_or_create_session()
    return SessionInfo(session_id=session_id, created=created)


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    if session_id in sessions:
        del sessions[session_id]
        logger.info(f"Deleted session: {session_id}")
        return {"message": "Session deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/api/session/{session_id}/reset")
async def reset_session(session_id: str):
    """Reset conversation history for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    sessions[session_id].reset_history()
    logger.info(f"Reset session: {session_id}")
    return {"message": "Session reset", "session_id": session_id}


@app.get("/api/files/{scholarship}/{wai}/{filename}")
async def get_file(scholarship: str, wai: str, filename: str):
    """
    Retrieve a file from the outputs directory.
    
    Args:
        scholarship: Scholarship name (e.g., Delaney_Wings)
        wai: WAI number
        filename: File name
        
    Returns:
        File content
    """
    # Construct file path
    file_path = OUTPUTS_DIR / scholarship / wai / "attachments" / filename
    
    # Security check - ensure path is within outputs directory
    try:
        file_path = file_path.resolve()
        OUTPUTS_DIR.resolve()
        if not str(file_path).startswith(str(OUTPUTS_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid path")
    
    # Check if file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)


@app.get("/api/scholarships")
async def list_scholarships():
    """List available scholarships."""
    try:
        scholarships = [d.name for d in OUTPUTS_DIR.iterdir() if d.is_dir()]
        return {"scholarships": scholarships}
    except Exception as e:
        logger.error(f"Error listing scholarships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket Endpoint
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat.
    
    Args:
        websocket: WebSocket connection
        session_id: Session identifier
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established: {session_id}")
    
    # Get or create session
    session_id, orchestrator, created = get_or_create_session(session_id)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "session_id": session_id,
            "created": created,
            "message": "Connected to scholarship chat agent"
        })
        
        # Message loop
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            message = data.get("message")
            scholarship = data.get("scholarship")
            
            if not message or not scholarship:
                await websocket.send_json({
                    "type": "error",
                    "error": "Missing message or scholarship"
                })
                continue
            
            # Process message
            try:
                response = orchestrator.chat(
                    message=message,
                    scholarship=scholarship
                )
                
                await websocket.send_json({
                    "type": "response",
                    "response": response,
                    "scholarship": scholarship
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": str(e)
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
        except:
            pass


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "sessions": len(sessions),
        "outputs_dir": str(OUTPUTS_DIR),
        "model": DEFAULT_MODEL
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Made with Bob
