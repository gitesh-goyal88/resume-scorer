import streamlit as st
from ui_utils import inject_custom_css

inject_custom_css()

st.markdown("<h1 class='gradient-title' style='font-size: 3rem; margin-bottom: 5px; padding-bottom: 5px;'>⚙️ Settings</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-heading'>Manage your account preferences and application settings.</p>", unsafe_allow_html=True)

st.markdown("<h3 style='margin-top: 24px; margin-bottom: 16px; color: #FAFAFA;'>Preferences</h3>", unsafe_allow_html=True)

# Container for settings
st.markdown('''
<div style='background: #18181B; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 24px;'>
''', unsafe_allow_html=True)

# Dark Mode (Locked On)
st.toggle("Dark Mode", value=True, disabled=True, key="setting_dark_mode")
st.markdown("<p style='color: #A1A1AA; font-size: 13px; margin-top: -10px; margin-bottom: 20px; font-family: Inter;'>Dark Mode is locked on to ensure the best premium experience.</p>", unsafe_allow_html=True)

# Email Notifications
st.toggle("Email Notifications", value=True, key="setting_email")
st.markdown("<p style='color: #A1A1AA; font-size: 13px; margin-top: -10px; margin-bottom: 20px; font-family: Inter;'>Receive weekly updates on your job applications and new job matches.</p>", unsafe_allow_html=True)

# Data Privacy
st.toggle("Share Anonymous Telemetry", value=False, key="setting_privacy")
st.markdown("<p style='color: #A1A1AA; font-size: 13px; margin-top: -10px; margin-bottom: 0px; font-family: Inter;'>Help us improve ResumeIQ by sharing anonymous usage statistics.</p>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<h3 style='margin-top: 32px; margin-bottom: 16px; color: #FAFAFA;'>Danger Zone</h3>", unsafe_allow_html=True)

st.markdown('''
<div style='background: #3F1D1D; border: 1px solid #EF4444; border-radius: 18px; padding: 24px; display: flex; justify-content: space-between; align-items: center;'>
    <div>
        <h4 style='color: #FAFAFA; margin: 0 0 4px 0;'>Delete Account</h4>
        <p style='color: #FCA5A5; margin: 0; font-size: 13px; font-family: Inter;'>Permanently delete your account and all associated data.</p>
    </div>
</div>
''', unsafe_allow_html=True)

if st.button("Delete Account", type="primary"):
    st.toast("This is a placeholder. Data deletion is not currently implemented.")
