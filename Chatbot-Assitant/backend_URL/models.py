from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

# SQLModel models for database
class Session(SQLModel, table=True):
    __tablename__ = "sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, unique=True)
    url: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationship with messages
    messages: List["Message"] = Relationship(back_populates="session")

class Message(SQLModel, table=True):
    __tablename__ = "messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.session_id")
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Relationship with session
    session: Optional[Session] = Relationship(back_populates="messages")

# Pydantic models for API
class ChatSession(BaseModel):
    session_id: str
    url: Optional[str] = None
    title: Optional[str] = None
    created_at: Optional[datetime] = None

class ChatHistory(BaseModel):
    session_id: str
    messages: List[Message]

class SummarizeRequest(BaseModel):
    url: str
    session_id: Optional[str] = None

class ChatRequest(BaseModel):
    session_id: str
    message: str 