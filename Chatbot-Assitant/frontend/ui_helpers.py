import streamlit as st
import requests
import json
import os
import pathlib
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import time
from datetime import datetime

# Load environment variables from parent directory
parent_dir = pathlib.Path(__file__).parent.parent.absolute()
load_dotenv(dotenv_path=os.path.join(parent_dir, ".env"))

PDF_API_URL = os.getenv("PDF_API_URL", "http://localhost:8000")
URL_API_URL = os.getenv("URL_API_URL", "http://localhost:8001")
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    st.error("API_KEY environment variable is not set")

# Headers for API requests
HEADERS = {"X-API-Key": API_KEY}

def get_api_url(source_type: str) -> str:
    """Return the appropriate API URL based on source type"""
    if source_type == "PDF":
        return PDF_API_URL
    elif source_type == "URL":
        return URL_API_URL
    else:
        # Default to PDF API if source type is not specified
        return PDF_API_URL

def upload_pdf(file) -> Dict[str, Any]:
    """Upload and summarize a PDF file with automatic session refresh"""
    if file is None:
        st.error("Please upload a PDF file")
        return None
    
    # Check file size
    file_size_mb = file.size / (1024 * 1024)
    if file_size_mb > 15:
        st.error(f"File size ({file_size_mb:.1f}MB) exceeds the maximum limit of 15MB")
        return None
    
    files = {"file": file}
    session_id = st.session_state.get("session_id", None)
    
    data = {}
    if session_id:
        data["session_id"] = session_id
    
    # Display file information
    st.info(f"Processing PDF: {file.name} ({file_size_mb:.1f}MB)")
    
    # Display progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Show first stage
        progress_bar.progress(0.1)
        status_text.text("Uploading PDF... (10%)")
        
        # TECHNOLOGY: Requests Library for API Communication
        # Using the Requests library to make HTTP POST requests to the backend API
        # This demonstrates uploading files and sending form data to a FastAPI endpoint
        response = requests.post(
            f"{PDF_API_URL}/summarize",
            files=files,
            data=data,
            headers=HEADERS,
            timeout=60  # Shorter timeout since we're only waiting for upload
        )
        
        if response.status_code != 200:
            if response.status_code in [401, 403]:
                st.error("Authentication failed. Invalid API key.")
            else:
                st.error(f"Error: {response.text}")
            progress_bar.empty()
            status_text.empty()
            return None
        
        result = response.json()
        session_id = result.get("session_id")
        
        # Update session_id in state
        if session_id:
            st.session_state.session_id = session_id
            # Clear old messages when uploading a new PDF
            st.session_state.messages = []
        
        # Display processing progress
        progress_bar.progress(0.3)
        status_text.text("PDF uploaded. Extracting text... (30%)")
        
        # Wait and check summary status
        max_wait = 10  # Only wait up to 10 seconds to display progress
        for i in range(max_wait):
            progress_value = 0.3 + (i / max_wait) * 0.6
            progress_bar.progress(progress_value)
            status_text.text(f"Processing document {file.name}... ({int(progress_value * 100)}%)")
            time.sleep(1)
        
        # Complete UI progress
        progress_bar.progress(1.0)
        status_text.text(f"Document {file.name} uploaded and processing! (100%)")
        time.sleep(0.5)
        
        # Clear progress bar and status
        progress_bar.empty()
        status_text.empty()
        
        # Display notification
        st.success(f"PDF {file.name} uploaded successfully! The summary is being generated in the background and will appear shortly.")
        
        # Mark that sessions list needs refreshing
        st.session_state.refresh_sessions = True
        
        return {
            "session_id": session_id,
            "summary": f"Processing summary of {file.name} in background. Please wait or start asking questions.",
            "filename": file.name
        }
        
    except requests.exceptions.Timeout:
        st.error("Request timed out during upload. Please try again with a smaller file.")
        progress_bar.empty()
        status_text.empty()
        return None
    except Exception as e:
        st.error(f"Error during processing: {str(e)}")
        progress_bar.empty()
        status_text.empty()
        return None

def check_summary_status(session_id: str) -> Dict[str, Any]:
    """Check the status of a summary being generated in the background"""
    try:
        # TECHNOLOGY: Requests Library for API GET Requests
        # Using the Requests library to make HTTP GET requests with parameters
        # This demonstrates retrieving data from a FastAPI endpoint with authentication
        response = requests.get(
            f"{PDF_API_URL}/summary/{session_id}",
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": f"Error: {response.text}"}
    except Exception as e:
        return {"status": "error", "message": f"Error checking summary status: {str(e)}"}

def process_url(url: str) -> Dict[str, Any]:
    """Process and summarize a URL"""
    if not url:
        st.error("Please enter a URL")
        return None
    
    # Always create a new session for a new URL
    session_id = None  # Don't use current session_id
    
    data = {
        "url": url
    }
    
    # Display progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Show first stage
        progress_bar.progress(0.1)
        status_text.text("Connecting to URL... (10%)")
        
        # TECHNOLOGY: Requests with JSON Payload
        # Using the Requests library to send JSON data to the backend API
        # This demonstrates sending structured data in the request body
        response = requests.post(
            f"{URL_API_URL}/summarize-url",
            json=data,
            headers=HEADERS,
            timeout=60
        )
        
        if response.status_code != 200:
            if response.status_code in [401, 403]:
                st.error("Authentication failed. Invalid API key.")
            else:
                st.error(f"Error: {response.text}")
            progress_bar.empty()
            status_text.empty()
            return None
        
        result = response.json()
        session_id = result.get("session_id")
        
        # Update session_id in state
        if session_id:
            st.session_state.session_id = session_id
        
        # Display processing progress
        progress_bar.progress(0.3)
        status_text.text("URL connected. Extracting content... (30%)")
        
        # Wait and display progress
        max_wait = 10  # Only wait up to 10 seconds to display progress
        for i in range(max_wait):
            progress_value = 0.3 + (i / max_wait) * 0.6
            progress_bar.progress(progress_value)
            status_text.text(f"Processing URL {url}... ({int(progress_value * 100)}%)")
            time.sleep(1)
        
        # Complete UI progress
        progress_bar.progress(1.0)
        status_text.text(f"URL {url} processed successfully! (100%)")
        time.sleep(0.5)
        
        # Clear progress bar and status
        progress_bar.empty()
        status_text.empty()
        
        # Mark that sessions list needs refreshing
        st.session_state.refresh_sessions = True
        
        # Clear session cache to force refresh
        if "sessions" in st.session_state:
            del st.session_state["sessions"]
        
        # Refresh session list immediately
        try:
            # Call API directly to refresh cache
            requests.get(
                f"{URL_API_URL}/sessions",
                headers=HEADERS,
                params={"cache_buster": time.time(), "force_refresh": "true"},
                timeout=2
            )
        except:
            pass
        
        # Set refresh time to 0 to force refresh
        st.session_state.last_refresh_time = 0
        
        # Log for debugging
        print(f"Created new URL session: {session_id} for URL: {url}")
        
        return result
        
    except requests.exceptions.Timeout:
        st.error("Request timed out during URL processing. Please try again.")
        progress_bar.empty()
        status_text.empty()
        return None
    except Exception as e:
        st.error(f"Error during URL processing: {str(e)}")
        progress_bar.empty()
        status_text.empty()
        return None

def send_message(session_id: str, message: str, source_type: str = None) -> str:
    """Send a message to the API and return the response"""
    try:
        # Determine which API endpoint to use based on source_type
        api_url = get_api_url(source_type)
        
        response = requests.post(
            f"{api_url}/chat",
            headers=HEADERS,
            json={
                "session_id": session_id,
                "message": message
            }
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        elif response.status_code in [401, 403]:
            st.error("Authentication failed. Invalid API key.")
            return ""
        else:
            st.error(f"Error: {response.text}")
            return ""
    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        return ""

def get_chat_history(session_id: str, source_type: str = None) -> List[Dict[str, Any]]:
    """Get chat history for a session"""
    if not session_id:
        print("Warning: Attempted to get chat history with empty session_id")
        return []
    
    # Log để debug
    print(f"Loading chat history for session_id: {session_id}, source_type: {source_type}")
    
    api_url = get_api_url(source_type)
    
    try:
        response = requests.get(
            f"{api_url}/history/{session_id}",
            headers=HEADERS,
            timeout=10  # Add timeout to prevent hanging
        )
        
        if response.status_code == 200:
            messages = response.json()["messages"]
            print(f"Successfully loaded {len(messages)} messages from session {session_id}")
            return messages
        elif response.status_code in [401, 403]:
            st.error("Authentication failed. Invalid API key.")
            return []
        else:
            error_msg = f"Error fetching chat history: {response.text}"
            print(error_msg)
            st.error(error_msg)
            return []
    except requests.exceptions.Timeout:
        st.error("Request timed out while loading chat history. Please try again.")
        return []
    except Exception as e:
        error_msg = f"Error fetching chat history: {str(e)}"
        print(error_msg)
        st.error(error_msg)
        return []

def get_all_sessions(source_type: str = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Get all chat sessions from both backends with automatic refresh"""
    # If sessions already in session_state and no force refresh needed, return immediately
    if "sessions" in st.session_state and not force_refresh:
        return st.session_state.sessions
    
    pdf_sessions = []
    url_sessions = []
    
    # Add cache_buster parameter to avoid cache when force_refresh=True
    cache_param = {}
    if force_refresh:
        cache_param = {"cache_buster": time.time(), "force_refresh": "true"}
    
    # Get PDF sessions
    try:
        response = requests.get(
            f"{PDF_API_URL}/sessions",
            headers=HEADERS,
            params=cache_param,
            timeout=5
        )
        
        if response.status_code == 200:
            pdf_sessions = response.json()["sessions"]
            # Mark these sessions as PDF type and ensure each session has a unique identifier
            for session in pdf_sessions:
                session["source_type"] = "PDF"
                # Ensure session_id is present
                if "session_id" not in session or not session["session_id"]:
                    # Generate a temporary ID if none exists (shouldn't happen in normal operation)
                    session["session_id"] = f"pdf_{int(time.time())}_{len(pdf_sessions)}"
    except Exception as e:
        print(f"Error fetching PDF sessions: {str(e)}")
    
    # Get URL sessions
    try:
        # Always force refresh for URL sessions
        url_cache_param = {"cache_buster": time.time(), "force_refresh": "true"}
        
        response = requests.get(
            f"{URL_API_URL}/sessions",
            headers=HEADERS,
            params=url_cache_param,
            timeout=5
        )
        
        if response.status_code == 200:
            url_sessions = response.json()["sessions"]
            # Mark these sessions as URL type
            for session in url_sessions:
                session["source_type"] = "URL"
                
                # Ensure session_id is present
                if "session_id" not in session or not session["session_id"]:
                    # Generate a temporary ID if none exists (shouldn't happen in normal operation)
                    session["session_id"] = f"url_{int(time.time())}_{len(url_sessions)}"
                
                # Ensure URL sessions have full display title
                if "title" in session and session["title"]:
                    # Truncate title if too long
                    title = session["title"]
                    if len(title) > 30:
                        title = title[:27] + "..."
                    session["display_title"] = title
                else:
                    # Use URL if no title
                    url = session.get("url", "Unknown URL")
                    if len(url) > 30:
                        url = url[:27] + "..."
                    session["display_title"] = url
    except Exception as e:
        print(f"Error fetching URL sessions: {str(e)}")
    
    # Sort sessions by creation time (newest first)
    all_sessions = pdf_sessions + url_sessions
    
    # Ensure each session has a created_at field
    for session in all_sessions:
        if "created_at" not in session or not session["created_at"]:
            session["created_at"] = "2000-01-01T00:00:00"  # Old default value
    
    # Check for duplicate session IDs
    session_ids = {}
    for i, session in enumerate(all_sessions):
        session_id = session["session_id"]
        if session_id in session_ids:
            # If duplicate ID found, add suffix to differentiate
            all_sessions[i]["session_id"] = f"{session_id}_{i}"
            print(f"Warning: Found duplicate session ID {session_id}, modified to {all_sessions[i]['session_id']}")
        else:
            session_ids[session_id] = True
    
    # Sort by creation time (newest first)
    all_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Save to session_state for future use
    st.session_state.sessions = all_sessions
    
    return all_sessions

def display_message(role: str, content: str):
    """Display a chat message with appropriate styling"""
    if role == "user":
        st.markdown(f"**You:** {content}")
    else:
        st.markdown(f"**Assistant:** {content}")

def clear_chat_history(session_id: str, source_type: str = None) -> bool:
    """Clear chat history for a session"""
    try:
        api_url = get_api_url(source_type)
        
        response = requests.delete(
            f"{api_url}/history/{session_id}",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            return True
        elif response.status_code in [401, 403]:
            st.error("Authentication failed. Invalid API key.")
            return False
        else:
            st.error(f"Error clearing chat history: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error clearing chat history: {str(e)}")
        return False

def delete_session(session_id: str, source_type: str = None) -> bool:
    """Delete a session and all its messages"""
    if not session_id:
        print("Warning: Attempted to delete session with empty session_id")
        return False
    
    try:
        api_url = get_api_url(source_type)
        
        # Log to help with debugging
        print(f"Deleting session: {session_id} from API: {api_url}")
        
        response = requests.delete(
            f"{api_url}/session/{session_id}",
            headers=HEADERS,
            timeout=10  # Add timeout to prevent hanging
        )
        
        # Log the response for debugging
        print(f"Delete session response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            # Check if sessions cache exists and remove this session
            if "sessions" in st.session_state:
                # Filter out the deleted session
                st.session_state.sessions = [
                    s for s in st.session_state.sessions 
                    if s.get("session_id") != session_id
                ]
                print(f"Removed session {session_id} from session cache. Remaining: {len(st.session_state.sessions)}")
            
            # Force refresh the sessions list to ensure UI is updated
            # This needs to be after the function is defined, so we'll handle it in the app.py instead
            return True
        elif response.status_code in [401, 403]:
            st.error("Authentication failed. Invalid API key.")
            return False
        else:
            error_msg = f"Error deleting session: {response.text}"
            print(error_msg)
            st.error(error_msg)
            return False
    except requests.exceptions.Timeout:
        st.error("Request timed out while deleting session. Please try again.")
        return False
    except Exception as e:
        error_msg = f"Error deleting session: {str(e)}"
        print(error_msg)
        st.error(error_msg)
        return False

def force_refresh_sessions():
    """Force an immediate refresh of the sessions list in both backends"""
    try:
        # Reset the sessions cache
        if "sessions" in st.session_state:
            del st.session_state["sessions"]
        
        # Reset refresh timestamp
        st.session_state.last_refresh_time = 0
        
        # Set refresh flag
        st.session_state.refresh_sessions = True
        
        # Force refresh PDF sessions
        try:
            cache_buster = str(time.time())
            requests.get(
                f"{PDF_API_URL}/sessions",
                headers=HEADERS,
                params={"cache_buster": cache_buster, "force_refresh": "true"},
                timeout=2
            )
        except Exception as e:
            print(f"Error refreshing PDF sessions: {str(e)}")
        
        # Force refresh URL sessions
        try:
            cache_buster = str(time.time())
            requests.get(
                f"{URL_API_URL}/sessions",
                headers=HEADERS,
                params={"cache_buster": cache_buster, "force_refresh": "true"},
                timeout=2
            )
        except Exception as e:
            print(f"Error refreshing URL sessions: {str(e)}")
        
        # Get all sessions with force refresh
        sessions = get_all_sessions(force_refresh=True)
        print(f"Force refreshed sessions, found {len(sessions)} sessions")
        
        return True
    except Exception as e:
        print(f"Error in force_refresh_sessions: {str(e)}")
        return False 