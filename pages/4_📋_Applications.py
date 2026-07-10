import streamlit as st
import pandas as pd
from database import insert_application, get_all_applications, update_application_status
from ui_utils import inject_custom_css
inject_custom_css()

st.markdown("""
<style>
    .kanban-col { background: #111216; padding: 16px; border-radius: 18px; border: 1px solid rgba(255,255,255,0.04); min-height: 500px; margin-top: 10px; }
    .job-card { background: #18181B; padding: 16px; border-radius: 12px; border-left: 4px solid #22C55E; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 12px; border-top: 1px solid rgba(255,255,255,0.08); border-right: 1px solid rgba(255,255,255,0.08); border-bottom: 1px solid rgba(255,255,255,0.08); transition: transform 0.2s ease; }
    .job-card:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.2); }
    .job-title { margin: 0 0 5px 0; font-size: 15px; color: #FAFAFA !important; font-family: "Inter", sans-serif; font-weight: 700; }
    .job-company { margin: 0 0 10px 0; font-size: 13px; color: #A1A1AA !important; font-family: "Inter", sans-serif; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='gradient-title' style='font-size: 3rem; margin-bottom: 5px; padding-bottom: 5px;'>📋 Application Tracker</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-heading'>Manage your job search pipeline just like a sales CRM. Keep track of what you've applied to and your interview progress.</p>", unsafe_allow_html=True)

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
        
        submitted = st.form_submit_button("Track Job", type="primary")
        if submitted and company and role:
            insert_application(company, role, status, url)
            st.success("Job tracked!")
            st.rerun()

st.markdown("<hr style='border: 0; height: 1px; background: rgba(255,255,255,0.08); margin: 30px 0;'>", unsafe_allow_html=True)

# 2. Kanban Board
apps = get_all_applications()
df = pd.DataFrame(apps) if apps else pd.DataFrame(columns=["id", "company", "role", "status", "url", "timestamp"])

status_cols = ["Wishlist", "Applied", "Interviewing", "Offer", "Rejected"]
cols = st.columns(len(status_cols))

for idx, status in enumerate(status_cols):
    with cols[idx]:
        st.markdown(f"<h3 style='margin: 0; font-size: 16px; color: #FAFAFA; text-align: center;'>{status}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin: 4px 0 0 0; font-size: 12px; color: #A1A1AA; text-align: center;'>{len(df[df['status'] == status]) if not df.empty else 0} jobs</p>", unsafe_allow_html=True)
        
        st.markdown("<div class='kanban-col'>", unsafe_allow_html=True)
        
        if not df.empty:
            status_df = df[df['status'] == status]
            for _, row in status_df.iterrows():
                # Color code borders based on status
                border_color = "#22C55E" if status in ["Offer", "Applied"] else "#F59E0B" if status in ["Interviewing", "Wishlist"] else "#EF4444"
                
                st.markdown(f"""
                <div class='job-card' style='border-left: 4px solid {border_color};'>
                    <h4 class='job-title'>{row['role']}</h4>
                    <p class='job-company'>🏢 {row['company']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Dropdown to move statuses
                new_status = st.selectbox(
                    "Move", 
                    status_cols, 
                    index=status_cols.index(status), 
                    key=f"status_{row['id']}",
                    label_visibility="collapsed"
                )
                if new_status != status:
                    update_application_status(row['id'], new_status)
                    st.rerun()
                    
        st.markdown("</div>", unsafe_allow_html=True)
