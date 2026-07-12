import streamlit as st

st.set_page_config(
    page_title="ResumeIQ | AI Candidate OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
if 'theme_accent' not in st.session_state:
    st.session_state.theme_accent = "Green"

from ui_utils import inject_custom_css
inject_custom_css()

# --- Auth Gateway ---
if st.session_state.user_id is None:
    # Hide sidebar completely on login page to prevent confusion
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}
        
        /* Fix mobile distortion by hiding empty padding columns */
        @media (max-width: 768px) {
            [data-testid="column"]:nth-of-type(1),
            [data-testid="column"]:nth-of-type(3) {
                display: none !important;
            }
            [data-testid="column"]:nth-of-type(2) {
                width: 100% !important;
                min-width: 100% !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Use responsive clamp() for fonts so mobile view doesn't break
    st.markdown("<h1 class='gradient-title' style='text-align: center; font-size: clamp(2rem, 6vw, 3.5rem); margin-bottom: 5px; padding-bottom: 10px;'>ResumeIQ Platform</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: clamp(0.9rem, 3vw, 1.2rem); color: #94A3B8;'>Welcome to the world's smartest AI Candidate OS.</p>", unsafe_allow_html=True)
    
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
    # Get active colors to render logo block matching the accent
    accent = st.session_state.get("theme_accent", "Green")
    accent_colors = {
        "Blue": "#60A5FA", "Green": "#1ed760", "Red": "#fb7185", "Purple": "#a78bfa", "Amber": "#facc15"
    }
    glow_colors = {
        "Blue": "rgba(96, 165, 250, 0.3)", "Green": "rgba(30, 215, 96, 0.3)", 
        "Red": "rgba(251, 113, 133, 0.3)", "Purple": "rgba(167, 139, 250, 0.3)", "Amber": "rgba(250, 204, 21, 0.3)"
    }
    
    # 1. Premium Logo Header in Sidebar (matches PromptTunes style)
    st.sidebar.markdown(f"""
    <div style='display: flex; align-items: center; gap: 12px; margin-top: 10px; margin-bottom: 24px; padding-left: 12px;'>
        <div style='background-color: {accent_colors[accent]}; width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 12px {glow_colors[accent]};'>
            <span style='color: #000000; font-size: 20px; font-weight: bold;'>⚡</span>
        </div>
        <div>
            <h3 style='margin: 0; font-size: 18px; font-family: "Outfit", sans-serif; color: #F4F4F5;'>ResumeIQ</h3>
            <p style='margin: 0; font-size: 11px; color: #71717A; font-family: "Plus Jakarta Sans", sans-serif;'>AI Candidate OS</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Sidebar UI customization (Theme Picker)
    st.sidebar.markdown("<p style='color: #94A3B8; font-size: 13px; font-weight: 600; margin-bottom: 8px; padding-left: 12px;'>THEME</p>", unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.sidebar.columns(5)
    
    # Render clickable color circles
    if c1.button("🔵", help="Blue Theme", use_container_width=True):
        st.session_state.theme_accent = "Blue"
        st.rerun()
    if c2.button("🟢", help="Green Theme", use_container_width=True):
        st.session_state.theme_accent = "Green"
        st.rerun()
    if c3.button("🔴", help="Red Theme", use_container_width=True):
        st.session_state.theme_accent = "Red"
        st.rerun()
    if c4.button("🟣", help="Purple Theme", use_container_width=True):
        st.session_state.theme_accent = "Purple"
        st.rerun()
    if c5.button("🟡", help="Amber Theme", use_container_width=True):
        st.session_state.theme_accent = "Amber"
        st.rerun()
        
    inject_custom_css()
    
    st.sidebar.markdown("---")

    # 3. Sidebar Navigation (Manual Rendering for absolute control)
    st.sidebar.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    pages = [
        st.Page("pages/1_🏠_Dashboard.py", title="Dashboard", icon="🏠"),
        st.Page("pages/2_📊_Resume_Analysis.py", title="Resume Analysis", icon="📊"),
        st.Page("pages/3_💼_Job_Matches.py", title="Job Matches", icon="💼"),
        st.Page("pages/5_🎙️_Interview_Prep.py", title="Interview Prep", icon="🎙️"),
        st.Page("pages/6_📈_Analytics.py", title="Analytics", icon="📈"),
        st.Page("pages/7_🏆_Leaderboard.py", title="Leaderboard", icon="🏆"),
        st.Page("pages/5_🎯_Jobscan_Matcher.py", title="Jobscan Matcher", icon="🎯")
    ]
    
    for p in pages:
        st.sidebar.page_link(p, label=p.title, icon=p.icon)
        
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout_user()
        st.rerun()
            
    # Run hidden native navigation
    pg = st.navigation(pages, position="hidden")
    pg.run()
