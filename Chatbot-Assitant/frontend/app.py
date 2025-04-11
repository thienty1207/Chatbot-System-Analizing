import streamlit as st
import time
import os
import pathlib
from dotenv import load_dotenv
from ui_helpers import (
    upload_pdf, send_message, get_chat_history, get_all_sessions, 
    display_message, clear_chat_history, delete_session, process_url, check_summary_status, force_refresh_sessions
)
from datetime import datetime

# Load environment variables from parent directory
parent_dir = pathlib.Path(__file__).parent.parent.absolute()
load_dotenv(dotenv_path=os.path.join(parent_dir, ".env"))

# Check if API key is set
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    # TECHNOLOGY: Streamlit Error Messages
    # Using Streamlit's error messages for user-friendly error handling
    # This clearly communicates configuration issues to the user
    st.error("API_KEY environment variable is not set. Please configure your .env file.")
    st.stop()

# TECHNOLOGY: Streamlit Page Configuration
# Setting up the Streamlit page layout and title
# This configures the overall appearance and behavior of the web application
st.set_page_config(
    page_title="AI Chatbot",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "source_type" not in st.session_state:
    st.session_state.source_type = None

# Track when sessions list needs refreshing
if "refresh_sessions" not in st.session_state:
    st.session_state.refresh_sessions = False

# Track if a session was recently deleted
if "session_recently_deleted" not in st.session_state:
    st.session_state.session_recently_deleted = False

# Track last refresh time
if "last_refresh_time" not in st.session_state:
    st.session_state.last_refresh_time = time.time()

# If a session was recently deleted, force refresh the sessions list
if st.session_state.get("session_recently_deleted", False):
    # Reset flag
    st.session_state.session_recently_deleted = False
    # Force refresh sessions list
    force_refresh_sessions()

# TECHNOLOGY: Streamlit UI - Main Title
# Creating the main application title with Streamlit
# This sets the primary heading for the application interface
st.title("Ho Thien Ty AI Chatbot")

# TECHNOLOGY: Streamlit Sidebar Layout
# Using Streamlit's sidebar for navigation and controls
# This creates a clean separation between content and controls
with st.sidebar:
    st.header("Choose Input Source")
    # TECHNOLOGY: Streamlit Interactive Widgets - Radio Buttons
    # Using Streamlit's radio buttons for option selection
    # This creates an intuitive UI for choosing between input types
    source_type = st.radio("Select source type:", ["PDF", "URL"])
    
    if source_type == "PDF":
        st.header("Upload PDF")
        # TECHNOLOGY: Streamlit File Uploader
        # Using Streamlit's file uploader component for handling file uploads
        # This provides a user-friendly interface for selecting and uploading PDF files
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        
        if uploaded_file is not None:
            # TECHNOLOGY: Streamlit Interactive Widgets - Buttons
            # Using Streamlit's button component for user actions
            # This creates a clear call-to-action for processing the uploaded file
            if st.button("Process PDF"):
                # TECHNOLOGY: Streamlit Progress Indicators
                # Using Streamlit's spinner for indicating background processes
                # This provides visual feedback during long-running operations
                with st.spinner("Uploading PDF..."):
                    # Reset session state before uploading new PDF
                    st.session_state.messages = []
                    
                    result = upload_pdf(uploaded_file)
                    if result:
                        st.session_state.source_type = "PDF"
                        st.session_state.session_id = result["session_id"]
                        # TECHNOLOGY: Streamlit Notifications
                        # Using Streamlit's success message for confirmation feedback
                        # This provides clear success indicators to the user
                        st.success(f"PDF {uploaded_file.name} uploaded successfully!")
                        
                        # Add initial message
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": f"PDF {uploaded_file.name} is being processed. You can start asking questions while the summary is being generated."
                        })
                        
                        # Set a flag to check summary status
                        st.session_state.check_summary = True
                        st.session_state.current_pdf = uploaded_file.name
                        
                        # Mark that sessions list needs refreshing
                        st.session_state.refresh_sessions = True
                        
                        # TECHNOLOGY: Streamlit Page Control
                        # Using Streamlit's rerun function to refresh the page state
                        # This ensures the UI reflects the latest application state
                        st.rerun()
    else:  # URL option
        st.header("Enter URL")
        # TECHNOLOGY: Streamlit Input Fields
        # Using Streamlit's text input component for data entry
        # This creates a clean interface for entering URLs
        url_input = st.text_input("Enter a URL to analyze")
        
        if url_input:
            if st.button("Process URL"):
                result = process_url(url_input)
                if result:
                    st.session_state.source_type = "URL"
                    st.session_state.session_id = result["session_id"]
                    st.success(f"URL processed successfully!")
                    st.session_state.messages = []  # Clear messages for new URL
                    
                    # Add summary as first message
                    st.session_state.messages.append({"role": "assistant", "content": f"URL Summary ({result['title']}): {result['summary']}"})
                    
                    # Mark sessions list for refresh and reset refresh time
                    st.session_state.refresh_sessions = True
                    st.session_state.last_refresh_time = 0  # Force immediate refresh
                    
                    # Add new URL to session_state for immediate display in dropdown
                    if "recent_urls" not in st.session_state:
                        st.session_state.recent_urls = []
                    
                    # Add new URL to beginning of list
                    st.session_state.recent_urls.insert(0, {
                        "session_id": result["session_id"],
                        "url": url_input,
                        "title": result["title"],
                        "source_type": "URL",
                        "display_title": result["title"] if len(result["title"]) <= 30 else result["title"][:27] + "..."
                    })
                    
                    st.rerun()
    
    # TECHNOLOGY: Streamlit UI Sections
    # Using Streamlit's divider to create clear visual separation between UI sections
    # This improves the organization and readability of the interface
    st.divider()
    
    # Session management
    st.header("Previous Sessions")
    
    # Automatically refresh sessions list when:
    # 1. Page is first loaded
    # 2. After uploading new PDF or processing new URL
    # 3. Every 30 seconds
    current_time = time.time()
    should_refresh = (
        current_time - st.session_state.last_refresh_time > 30 or  # Every 30 seconds
        st.session_state.get("refresh_sessions", False) or  # After uploading new PDF or processing new URL
        "sessions" not in st.session_state  # Sessions not yet in session_state
    )
    
    # Always force refresh after processing new URL
    if st.session_state.get("refresh_sessions", False):
        print("Forcing session list refresh due to new URL processing")
        should_refresh = True
    
    if should_refresh:
        # Force refresh when needed
        sessions = get_all_sessions(force_refresh=True)
        st.session_state.last_refresh_time = current_time
        st.session_state.refresh_sessions = False
        
        # Log for debugging
        print(f"Refreshed sessions list, found {len(sessions)} sessions")
        for s in sessions:
            if "url" in s and s["url"]:
                print(f"  - URL Session: {s.get('session_id')[:8]}... Title: {s.get('title')}")
            elif "pdf_name" in s and s["pdf_name"]:
                print(f"  - PDF Session: {s.get('session_id')[:8]}... Name: {s.get('pdf_name')}")
    else:
        # No force refresh when not needed
        sessions = get_all_sessions(force_refresh=False)
    
    # TECHNOLOGY: Streamlit Text Elements
    # Using Streamlit's caption for displaying supplementary information
    # This adds context information without dominating the interface
    last_update = time.strftime("%H:%M:%S", time.localtime(st.session_state.last_refresh_time))
    st.caption(f"Last updated: {last_update}")
    
    if sessions:
        # Determine if each session is PDF or URL based
        session_options = []
        session_id_map = {}  # Map from display option to session ID
        
        for s in sessions:
            if "pdf_name" in s and s["pdf_name"]:
                display_option = f"PDF: {s['pdf_name']} ({s['session_id'][:8]}...)"
                session_options.append(display_option)
                session_id_map[display_option] = s
            elif "url" in s and s["url"]:
                # Use display_title if available, otherwise use title or url
                title = s.get("display_title", s.get("title", "No title"))
                display_option = f"URL: {title} ({s['session_id'][:8]}...)"
                session_options.append(display_option)
                session_id_map[display_option] = s
            else:
                display_option = f"Session: ({s['session_id'][:8]}...)"
                session_options.append(display_option)
                session_id_map[display_option] = s
        
        # Debug to track sessions
        print(f"Available sessions: {len(session_options)}")
        for opt in session_options:
            print(f"  - {opt} (ID: {session_id_map[opt]['session_id']})")
        
        # Use variable to store previously selected session
        if "previous_selection" not in st.session_state:
            st.session_state.previous_selection = None
        
        # Select default session (current session if available)
        default_index = 0
        if st.session_state.session_id:
            # Find current session in list
            for i, opt in enumerate(session_options):
                session = session_id_map[opt]
                if session["session_id"] == st.session_state.session_id:
                    default_index = i
                    break
        
        # Add field to store session selection in session state
        if "session_selector_value" not in st.session_state:
            st.session_state.session_selector_value = None
        
        # Callback to track selectbox change
        def on_session_select():
            selected = st.session_state.session_selector
            if selected != st.session_state.session_selector_value:
                st.session_state.session_selector_value = selected
                print(f"Session selection changed to: {selected}")
                
                # Reset flag to ensure session will be reloaded
                st.session_state.previous_selection = None
        
        selected_session = st.selectbox(
            "Select a previous session",
            options=session_options,
            index=default_index,
            key="session_selector",
            on_change=on_session_select
        )
        
        # Show load session button for clarity
        if st.button("Load Selected Session", type="primary"):
            selected_session_data = session_id_map[selected_session]
            session_id = selected_session_data["session_id"]
            
            print(f"Explicitly loading session: {selected_session} (ID: {session_id})")
            
            # Reset previous messages
            st.session_state.messages = []
            
            # Set session ID and source type
            st.session_state.session_id = session_id
            st.session_state.source_type = selected_session_data["source_type"]
            
            # Load messages
            history = get_chat_history(session_id, st.session_state.source_type)
            st.session_state.messages = history
            
            # Update selection tracking
            st.session_state.previous_selection = selected_session
            
            # Success notification
            st.success(f"Loaded session: {selected_session}")
            
            # Refresh page to display new messages
            st.rerun()

# Main chat interface
st.header("Chat")

# Add Clear button that always shows - larger and more prominent
col1, col2 = st.columns([5, 1])
with col2:
    if st.button("Clear", type="primary", use_container_width=True):
        if st.session_state.session_id:
            # Delete session and all its messages
            current_session_id = st.session_state.session_id
            current_source_type = st.session_state.source_type
            
            if delete_session(current_session_id, current_source_type):
                # Reset session state
                st.session_state.session_id = None
                st.session_state.messages = []
                st.session_state.source_type = None
                
                # Set flag that a session was recently deleted
                st.session_state.session_recently_deleted = True
                
                # Force refresh sessions list to immediately update the dropdown
                force_refresh_sessions()
                
                # Reset session selector
                if "session_selector_value" in st.session_state:
                    st.session_state.session_selector_value = None
                if "previous_selection" in st.session_state:
                    st.session_state.previous_selection = None
                
                st.success("Chat history and session cleared successfully!")
                st.rerun()
            else:
                st.error("Failed to clear session")
        else:
            st.warning("No active session to clear")

# Handle user input
if prompt := st.chat_input("Ask a question about your document"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    display_message("user", prompt)
    
    with st.spinner("Thinking..."):
        # Only send the message if we have a valid session
        if st.session_state.session_id:
            response = send_message(st.session_state.session_id, prompt, st.session_state.source_type)
            
            if response:
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
                # Use st.rerun() instead of immediately displaying the message
                # This prevents multiple API calls
                st.rerun()
            else:
                st.error("Failed to get response from assistant")
        else:
            st.error("Please upload a PDF or enter a URL first, or select a session")

# Display chat messages
for message in st.session_state.messages:
    with st.container():
        if message["role"] == "user":
            st.markdown("### 🧑 User")
            st.markdown(f"<div style='background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 10px; color: black;'>{message['content']}</div>", unsafe_allow_html=True)
        else:
            if "PDF Summary:" in message['content']:
                summary_text = message['content'].replace("PDF Summary:", "").strip()
                st.markdown("### 🤖 AI - PDF Summary")
                st.markdown(f"<div style='background-color: #e6f3ff; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: black;'>{summary_text}</div>", unsafe_allow_html=True)
            else:
                st.markdown("### 🤖 AI")
                st.markdown(f"<div style='background-color: #e6f3ff; padding: 10px; border-radius: 10px; margin-bottom: 10px; color: black;'>{message['content']}</div>", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

# Footer
st.divider()
st.caption("Ho Thien Ty - DH21KPM01 - 213895")

# Add to chat display for checking summary status
if st.session_state.get("check_summary") and st.session_state.session_id:
    # Check summary status every time page is loaded
    summary_status = check_summary_status(st.session_state.session_id)
    
    if summary_status.get("status") == "completed":
        # If summary is completed, update first message
        if st.session_state.messages and "PDF is being processed" in st.session_state.messages[0]["content"]:
            st.session_state.messages[0] = {
                "role": "assistant", 
                "content": f"PDF Summary: {summary_status.get('summary', 'Summary completed.')}"
            }
            # Turn off check flag
            st.session_state.check_summary = False
            st.rerun() 