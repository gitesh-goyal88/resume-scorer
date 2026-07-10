import streamlit as st
import pandas as pd
from database import insert_application, get_all_applications, update_application_status
from ui_utils import inject_custom_css
inject_custom_css()

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    [data-testid="stAppDeployButton"] {display: none;}
    footer {visibility: hidden;}
    .kanban-col { background: #111827; padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.06); min-height: 400px; }
    .job-card { background: #1E293B; padding: 15px; border-radius: 8px; border-left: 4px solid #2563EB; box-shadow: 0 4px 6px rgba(0,0,0,0.15); margin-bottom: 15px; border-top: 1px solid rgba(255,255,255,0.04); border-right: 1px solid rgba(255,255,255,0.04); border-bottom: 1px solid rgba(255,255,255,0.04); }
    .job-title { margin: 0 0 5px 0; font-size: 16px; color: #F1F5F9 !important; font-family: "Outfit", sans-serif; font-weight: 600; }
    .job-company { margin: 0 0 10px 0; font-size: 14px; color: #94A3B8 !important; }
</style>
""", unsafe_allow_html=True)

st.title("📋 Application Tracker (CRM)")
st.markdown("Manage your job search pipeline just like a sales CRM. Keep track of what you've applied to and your interview progress.")

# 1. Add New Application
with st.expander("➕ Track a New Job Application"):
    with st.form("new_app_form"):
        c1, c2 = st.columns(2)
        with c1:
            company = st.text_input("Company Name")
            role = st.text_input("Job Title")
        with c2:
            status = st.selectbox("Current Status", ["Wishlist", "Applied", "Interviewing", "Offer", "Rejected"])
            url = st.text_input("Job Post URL (Optional)")
        
        submitted = st.form_submit_button("Track Job")
        if submitted and company and role:
            insert_application(company, role, status, url)
            st.success("Job tracked!")
            st.rerun()

st.markdown("---")

# 2. Kanban Board
apps = get_all_applications()
df = pd.DataFrame(apps) if apps else pd.DataFrame(columns=["id", "company", "role", "status", "url", "timestamp"])

status_cols = ["Wishlist", "Applied", "Interviewing", "Offer", "Rejected"]
cols = st.columns(len(status_cols))

for idx, status in enumerate(status_cols):
    with cols[idx]:
        st.markdown(f"### {status}")
        st.markdown("<div class='kanban-col'>", unsafe_allow_html=True)
        
        if not df.empty:
            status_df = df[df['status'] == status]
            for _, row in status_df.iterrows():
                st.markdown(f"""
                <div class='job-card'>
                    <h4 class='job-title'>{row['role']}</h4>
                    <p class='job-company'>🏢 {row['company']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Dropdown to move statuses
                new_status = st.selectbox(
                    "Move to:", 
                    status_cols, 
                    index=status_cols.index(status), 
                    key=f"status_{row['id']}",
                    label_visibility="collapsed"
                )
                if new_status != status:
                    update_application_status(row['id'], new_status)
                    st.rerun()
                    
        st.markdown("</div>", unsafe_allow_html=True)
