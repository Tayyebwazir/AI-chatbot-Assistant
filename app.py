import streamlit as st
import requests
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="AI Chatbot",
    page_icon="🤖",
    layout="wide"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"  # Change this to your FastAPI server URL

# Custom CSS
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
    }
    .assistant-message {
        background-color: #F1F8E9;
        border-left: 4px solid #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "current_session" not in st.session_state:
    st.session_state.current_session = f"chat_{int(time.time())}"

if "sessions" not in st.session_state:
    st.session_state.sessions = []

# API Functions
def check_health():
    """Check API health"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def create_session(session_name=None):
    """Create a new session"""
    try:
        data = {"session_name": session_name} if session_name else {}
        response = requests.post(f"{API_BASE_URL}/sessions", json=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error creating session: {str(e)}")
        return None

def get_sessions():
    """Get all sessions"""
    try:
        response = requests.get(f"{API_BASE_URL}/sessions", timeout=10)
        if response.status_code == 200:
            return response.json().get("sessions", [])
        return []
    except Exception as e:
        st.error(f"Error fetching sessions: {str(e)}")
        return []

def get_session_history(session_id):
    """Get session history"""
    try:
        response = requests.get(f"{API_BASE_URL}/sessions/{session_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None

def send_message(session_id, content, language="English"):
    """Send a message to the API"""
    try:
        data = {
            "content": content,
            "language": language
        }
        response = requests.post(
            f"{API_BASE_URL}/chat/{session_id}",
            json=data,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        return None

def delete_session(session_id):
    """Delete a session"""
    try:
        response = requests.delete(f"{API_BASE_URL}/sessions/{session_id}", timeout=10)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error deleting session: {str(e)}")
        return False

def clear_session(session_id):
    """Clear session history"""
    try:
        response = requests.post(f"{API_BASE_URL}/sessions/{session_id}/clear", timeout=10)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error clearing session: {str(e)}")
        return False

def display_messages(session_id):
    """Display chat messages"""
    history = get_session_history(session_id)
    
    if not history or len(history.get("messages", [])) == 0:
        st.info("👋 Start a conversation by typing a message below!")
        return
    
    for message in history["messages"]:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>👤 You:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
        elif message["role"] == "assistant":
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 Assistant:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)

def main():
    st.title("🤖 AI Chatbot Assistant")
    st.markdown("---")
    
    # Check API health
    if not check_health():
        st.error("❌ Cannot connect to API server. Please make sure the FastAPI server is running on " + API_BASE_URL)
        st.info("Run: `uvicorn main:app --reload` to start the server")
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Language selection
        language = st.selectbox(
            "🌐 Select Language",
            ["English", "Urdu", "Spanish", "French", "German"],
            index=0
        )
        
        st.markdown("---")
        
        # Session management
        st.subheader("💬 Sessions")
        
        # Current session
        st.write(f"**Current:** `{st.session_state.current_session}`")
        
        # Session buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🆕 New", use_container_width=True):
                new_session = f"chat_{int(time.time())}"
                result = create_session(new_session)
                if result:
                    st.session_state.current_session = result["session_id"]
                    st.success("Session created!")
                    st.rerun()
        
        with col2:
            if st.button("🗑️ Clear", use_container_width=True):
                if clear_session(st.session_state.current_session):
                    st.success("Session cleared!")
                    st.rerun()
        
        # Refresh sessions
        if st.button("🔄 Refresh Sessions", use_container_width=True):
            st.session_state.sessions = get_sessions()
            st.rerun()
        
        # Session selector
        sessions = get_sessions()
        if sessions:
            session_ids = [s["session_id"] for s in sessions]
            if st.session_state.current_session not in session_ids and session_ids:
                st.session_state.current_session = session_ids[0]
            
            selected = st.selectbox(
                "Switch Session",
                session_ids,
                index=session_ids.index(st.session_state.current_session) if st.session_state.current_session in session_ids else 0
            )
            if selected != st.session_state.current_session:
                st.session_state.current_session = selected
                st.rerun()
            
            # Delete session button
            if st.button("🗑️ Delete Current Session", use_container_width=True):
                if delete_session(st.session_state.current_session):
                    st.success("Session deleted!")
                    remaining_sessions = get_sessions()
                    if remaining_sessions:
                        st.session_state.current_session = remaining_sessions[0]["session_id"]
                    else:
                        st.session_state.current_session = f"chat_{int(time.time())}"
                    st.rerun()
        
        st.markdown("---")
        
        # Stats
        st.subheader("📊 Stats")
        sessions = get_sessions()
        current_history = get_session_history(st.session_state.current_session)
        
        st.metric("Sessions", len(sessions))
        st.metric("Messages", current_history["message_count"] if current_history else 0)
    
    # Main chat area
    st.subheader(f"💬 Session: {st.session_state.current_session}")
    
    # Display messages
    messages_container = st.container()
    with messages_container:
        display_messages(st.session_state.current_session)
    
    # Chat input
    st.markdown("---")
    
    # Input form
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "💭 Your message:",
            height=100,
            placeholder="Type your message here...",
            help="Press Ctrl+Enter to send"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit = st.form_submit_button("Send 📤", use_container_width=True)
    
    # Process input
    if submit and user_input.strip():
        with st.spinner("🤔 Thinking..."):
            response = send_message(st.session_state.current_session, user_input, language)
            
            if response:
                st.success("✅ Message sent!")
                time.sleep(0.5)
                st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
        "Powered by FastAPI + LangChain + Groq + Streamlit<br>"
        f"API Status: {'🟢 Connected' if check_health() else '🔴 Disconnected'}"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()