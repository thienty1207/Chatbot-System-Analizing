import os
import pathlib
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine, select, Field

from models import Session as ChatSession, Message

# Load environment variables from parent directory
parent_dir = pathlib.Path(__file__).parent.parent.absolute()
load_dotenv(dotenv_path=os.path.join(parent_dir, ".env"))

class ChatDatabase:
    def __init__(self, db_path=None):
        # Use environment variable for database path if not specified
        self.db_path = db_path or os.getenv("URL_DATABASE_PATH", "url_chat_history.db")
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self._create_tables()
    
    def _create_tables(self):
        SQLModel.metadata.create_all(self.engine)
    
    def create_session(self, session_id: str, url: Optional[str] = None, title: Optional[str] = None) -> bool:
        try:
            with Session(self.engine) as session:
                # Check if session already exists
                existing = session.exec(
                    select(ChatSession).where(ChatSession.session_id == session_id)
                ).first()
                
                if existing:
                    return False
                
                # Create new session
                new_session = ChatSession(session_id=session_id, url=url, title=title)
                session.add(new_session)
                session.commit()
                return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        try:
            with Session(self.engine) as session:
                # Create new message
                new_message = Message(
                    session_id=session_id,
                    role=role,
                    content=content
                )
                session.add(new_message)
                session.commit()
                return True
        except Exception as e:
            print(f"Error adding message: {e}")
            return False
    
    def get_session_messages(self, session_id: str) -> List[dict]:
        with Session(self.engine) as session:
            messages = session.exec(
                select(Message).where(Message.session_id == session_id).order_by(Message.timestamp)
            ).all()
            
            return [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                }
                for msg in messages
            ]
    
    def get_all_sessions(self) -> List[dict]:
        """Get all sessions with optimized performance"""
        try:
            with Session(self.engine) as session:
                # Xóa cache và làm mới dữ liệu
                session.expire_all()
                
                # Thực hiện truy vấn trực tiếp
                stmt = select(ChatSession).order_by(ChatSession.created_at.desc())
                result = session.exec(stmt).all()
                
                # Chuyển đổi kết quả thành danh sách dict
                sessions = []
                for s in result:
                    sessions.append({
                        "session_id": s.session_id,
                        "url": s.url,
                        "title": s.title,
                        "created_at": s.created_at.isoformat() if s.created_at else None
                    })
                
                return sessions
        except Exception as e:
            print(f"Error getting sessions: {e}")
            return []
    
    def clear_session_messages(self, session_id: str) -> bool:
        try:
            with Session(self.engine) as session:
                # Check if session exists
                existing = session.exec(
                    select(ChatSession).where(ChatSession.session_id == session_id)
                ).first()
                
                if not existing:
                    print(f"Session {session_id} not found")
                    return False
                
                # Delete all messages for the session
                messages = session.exec(
                    select(Message).where(Message.session_id == session_id)
                ).all()
                
                for msg in messages:
                    session.delete(msg)
                
                session.commit()
                print(f"Deleted {len(messages)} messages for session {session_id}")
                return True
        except Exception as e:
            print(f"Error clearing messages: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        try:
            with Session(self.engine) as session:
                # Check if session exists
                existing = session.exec(
                    select(ChatSession).where(ChatSession.session_id == session_id)
                ).first()
                
                if not existing:
                    print(f"Session {session_id} not found")
                    return False
                
                # Delete all messages for the session
                messages = session.exec(
                    select(Message).where(Message.session_id == session_id)
                ).all()
                
                for msg in messages:
                    session.delete(msg)
                
                # Delete the session itself
                session.delete(existing)
                
                session.commit()
                print(f"Deleted session {session_id} and all its messages")
                return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False 