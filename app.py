import streamlit as st
import subprocess
import sys

# Ensure Playwright library and Chromium binary are installed on startup (cached to run only once)
@st.cache_resource
def ensure_playwright_installed():
    try:
        import playwright
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
    
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch(headless=True)
    except Exception:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

ensure_playwright_installed()

from auth_utils import login_user, register_user, logout_user

st.set_page_config(
    page_title="ResumeIQ | AI Candidate OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide Streamlit elements and apply light mode css
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    [data-testid="stAppDeployButton"] {display: none;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Session State initialization
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# --- Auth Gateway ---
if st.session_state.user_id is None:
    st.markdown("<h1 style='text-align: center; color: #3B82F6;'>ResumeIQ Platform</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Welcome to the world's smartest AI Candidate OS.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
        
        with tab1:
            st.subheader("Login")
            l_user = st.text_input("Username", key="l_user")
            l_pass = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login", type="primary", use_container_width=True):
                if login_user(l_user, l_pass):
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
                    
        with tab2:
            st.subheader("Sign Up")
            r_name = st.text_input("Full Name", key="r_name")
            r_user = st.text_input("Username", key="r_user")
            r_pass = st.text_input("Password", type="password", key="r_pass")
            if st.button("Sign Up", type="primary", use_container_width=True):
                if register_user(r_name, r_user, r_pass):
                    st.success("Account created successfully! Please login.")
                else:
                    st.error("Username already exists.")
                    
else:
    # Top bar for logout
    c1, c2 = st.columns([8,1])
    with c2:
        if st.button("Logout"):
            logout_user()
            st.rerun()
            
    # Define pages
    pages = {
        "Candidate Tools": [
            st.Page("pages/1_🏠_Candidate_Portal.py", title="Upload & Enhance", icon="🏠"),
            st.Page("pages/2_💼_Job_Matches.py", title="Job Matches", icon="💼"),
            st.Page("pages/5_🎯_Jobscan_Matcher.py", title="Custom Job Scanner", icon="🎯"),
            st.Page("pages/6_📋_Application_Tracker.py", title="Application Tracker", icon="📋"),
            st.Page("pages/4_🎙️_Interview_Grader.py", title="Interview Grader", icon="🎙️"),
        ],
        "Academic IR": [
            st.Page("pages/4_🔍_Job_Search_Engine.py", title="Job Search Engine", icon="🔍"),
            st.Page("pages/5_📈_Evaluation_Metrics.py", title="Evaluation Metrics", icon="📈"),
        ],
        "Community": [
            st.Page("pages/7_🏆_Leaderboard.py", title="Global Leaderboard", icon="🏆"),
        ],
        "Enterprise Settings": [
            st.Page("pages/3_👔_HR_Dashboard.py", title="HR Admin Dashboard", icon="👔"),
        ]
    }

    # Run navigation
    pg = st.navigation(pages)
    pg.run()
