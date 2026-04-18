from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
import uuid
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AI Chatbot API",
    description="FastAPI backend for AI chatbot with session management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for sessions (use Redis/Database in production)
session_store: Dict[str, ChatMessageHistory] = {}

# Pydantic models
class ChatMessage(BaseModel):
    content: str
    language: Optional[str] = "English"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str

class SessionCreate(BaseModel):
    session_name: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    message_count: int
    created_at: str

class MessageHistory(BaseModel):
    role: str
    content: str

class SessionHistory(BaseModel):
    session_id: str
    messages: List[MessageHistory]
    message_count: int

# Initialize model
def get_model():
    """Initialize the ChatGroq model"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not found in environment variables")
    
    try:
        model = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=groq_api_key
        )
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing model: {str(e)}")

# Get or create session history
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Get or create session history"""
    if session_id not in session_store:
        session_store[session_id] = ChatMessageHistory()
    return session_store[session_id]

# Create conversation chain
def create_chain(model, language="English"):
    """Create the conversation chain"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a helpful assistant. Answer all questions to the best of your ability in {language}."),
        MessagesPlaceholder(variable_name="messages")
    ])
    
    chain = prompt | model
    return RunnableWithMessageHistory(chain, get_session_history)

# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "POST /chat/{session_id}": "Send a message",
            "POST /sessions": "Create a new session",
            "GET /sessions": "List all sessions",
            "GET /sessions/{session_id}": "Get session history",
            "DELETE /sessions/{session_id}": "Delete a session",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        model = get_model()
        return {
            "status": "healthy",
            "model": "llama3-8b-8192",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/sessions", response_model=SessionResponse)
async def create_session(session: SessionCreate):
    """Create a new chat session"""
    session_id = session.session_name or f"session_{uuid.uuid4().hex[:8]}"
    
    if session_id in session_store:
        raise HTTPException(status_code=400, detail="Session ID already exists")
    
    session_store[session_id] = ChatMessageHistory()
    
    return SessionResponse(
        session_id=session_id,
        message_count=0,
        created_at=datetime.now().isoformat()
    )

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    sessions = []
    for session_id, history in session_store.items():
        sessions.append({
            "session_id": session_id,
            "message_count": len(history.messages),
        })
    return {"sessions": sessions, "total": len(sessions)}

@app.get("/sessions/{session_id}", response_model=SessionHistory)
async def get_session(session_id: str):
    """Get session history"""
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    history = session_store[session_id]
    messages = []
    
    for msg in history.messages:
        if isinstance(msg, HumanMessage):
            messages.append(MessageHistory(role="user", content=msg.content))
        elif isinstance(msg, AIMessage):
            messages.append(MessageHistory(role="assistant", content=msg.content))
    
    return SessionHistory(
        session_id=session_id,
        messages=messages,
        message_count=len(messages)
    )

@app.post("/chat/{session_id}", response_model=ChatResponse)
async def chat(session_id: str, message: ChatMessage):
    """Send a message and get a response"""
    if not message.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty")
    
    # Create session if it doesn't exist
    if session_id not in session_store:
        session_store[session_id] = ChatMessageHistory()
    
    try:
        # Get model and create chain
        model = get_model()
        chain = create_chain(model, message.language)
        config = {"configurable": {"session_id": session_id}}
        
        # Invoke chain
        response = chain.invoke(
            {"messages": [HumanMessage(content=message.content)]},
            config=config
        )
        
        # Extract response content
        response_content = response.content if hasattr(response, 'content') else str(response)
        
        return ChatResponse(
            response=response_content,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del session_store[session_id]
    return {"message": f"Session {session_id} deleted successfully"}

@app.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """Clear session history"""
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_store[session_id].clear()
    return {"message": f"Session {session_id} cleared successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)