with open("pages/1_🏠_Dashboard.py", "r") as f:
    lines = f.readlines()

new_ui = """
# ── Main UI ────────────────────────────────────────────────────────────────────
# UI Customization styles are injected globally from ui_utils.py

# Global Search
st.markdown('''
<div style='margin-bottom: 30px; display: flex; gap: 10px; align-items: center;'>
    <h2 style='margin: 0; color: #FAFAFA; font-weight: 700; flex-grow: 1;'>Hello Gitesh 👋</h2>
    <input type='text' placeholder='Search jobs, resumes, reports...' style='padding: 10px 16px; border-radius: 99px; background: #18181B; border: 1px solid rgba(255,255,255,0.08); color: #FAFAFA; width: 300px; font-family: Inter; outline: none;' disabled>
</div>
''', unsafe_allow_html=True)

# Resume Health Component
if st.session_state.ats_ml_score:
    score = int(st.session_state.ats_ml_score["score"])
    health_label = "Excellent" if score >= 80 else "Good" if score >= 60 else "Needs Work"
    bar_width = f"{score}%"
    
    st.markdown(f'''
    <div style='background: #18181B; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 24px; margin-bottom: 24px;'>
        <div style='display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px;'>
            <div>
                <p style='margin: 0; color: #A1A1AA; font-size: 14px; font-weight: 500; font-family: Inter;'>Resume Health</p>
                <h1 style='margin: 0; color: #FAFAFA; font-size: 36px; font-weight: 800; line-height: 1.1;'>{score}% <span style='font-size: 18px; font-weight: 500; color: #22C55E;'>{health_label}</span></h1>
            </div>
        </div>
        <div style='background: #111216; height: 12px; border-radius: 99px; overflow: hidden; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.04);'>
            <div style='width: {bar_width}; background: #22C55E; height: 100%; border-radius: 99px;'></div>
        </div>
        <div style='display: flex; gap: 24px; flex-wrap: wrap;'>
            <div style='display: flex; align-items: center; gap: 8px;'><span style='color: #22C55E;'>✓</span><span style='color: #FAFAFA; font-size: 14px; font-family: Inter;'>ATS Friendly</span></div>
            <div style='display: flex; align-items: center; gap: 8px;'><span style='color: #22C55E;'>✓</span><span style='color: #FAFAFA; font-size: 14px; font-family: Inter;'>Grammar</span></div>
            <div style='display: flex; align-items: center; gap: 8px;'><span style='color: #22C55E;'>✓</span><span style='color: #FAFAFA; font-size: 14px; font-family: Inter;'>Skills</span></div>
            <div style='display: flex; align-items: center; gap: 8px;'><span style='color: #F59E0B;'>⚠</span><span style='color: #FAFAFA; font-size: 14px; font-family: Inter;'>Missing Keywords</span></div>
            <div style='display: flex; align-items: center; gap: 8px;'><span style='color: #22C55E;'>✓</span><span style='color: #FAFAFA; font-size: 14px; font-family: Inter;'>Formatting</span></div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

# Main Grid
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("<h3 style='margin-bottom: 16px; font-size: 18px;'>Resume Engine</h3>", unsafe_allow_html=True)
    
    # Upload Zone
    uploaded_file = st.file_uploader("Upload your latest resume (PDF)", type=["pdf"], label_visibility="collapsed")
    
    if not st.session_state.resume_text:
        st.markdown('''
        <div style='background: #18181B; border: 1px dashed rgba(255,255,255,0.15); border-radius: 18px; padding: 40px; text-align: center; margin-top: 20px;'>
            <h3 style='color: #FAFAFA; margin-bottom: 8px;'>No resume analyzed yet.</h3>
            <p style='color: #A1A1AA; font-family: Inter; margin-bottom: 24px;'>Upload your resume to unlock:</p>
            <div style='display: flex; justify-content: center; gap: 24px; flex-wrap: wrap;'>
                <div style='color: #FAFAFA; font-size: 14px;'><span style='color: #22C55E; margin-right: 6px;'>✓</span>ATS Analysis</div>
                <div style='color: #FAFAFA; font-size: 14px;'><span style='color: #22C55E; margin-right: 6px;'>✓</span>Job Matching</div>
                <div style='color: #FAFAFA; font-size: 14px;'><span style='color: #22C55E; margin-right: 6px;'>✓</span>Salary Prediction</div>
                <div style='color: #FAFAFA; font-size: 14px;'><span style='color: #22C55E; margin-right: 6px;'>✓</span>Interview Prep</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
    else:
        # Show Metrics
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        
        with m1:
            st.markdown(f"<div class='info-card'><h3>{int(st.session_state.ats_ml_score['score'])}/100</h3><p>ATS Score</p></div>", unsafe_allow_html=True)
        with m2:
            st.markdown(f"<div class='info-card'><h3>{len(st.session_state.skills or [])} Skills</h3><p>Resume Strength</p></div>", unsafe_allow_html=True)
        with m3:
            st.markdown(f"<div class='info-card'><h3>15+ Active</h3><p>Job Matches</p></div>", unsafe_allow_html=True)
        with m4:
            st.markdown(f"<div class='info-card'><h3>Ready</h3><p>Interview Prep</p></div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("📊 View Full ATS Report", use_container_width=True, type="primary"):
                st.switch_page("pages/2_📊_Resume_Analysis.py")
        with col_btn2:
            if st.button("💼 View Job Matches", use_container_width=True, type="secondary"):
                st.switch_page("pages/3_💼_Job_Matches.py")

with col_right:
    st.markdown("<h3 style='margin-bottom: 16px; font-size: 18px;'>Recent Activity</h3>", unsafe_allow_html=True)
    
    if not st.session_state.resume_text:
        st.markdown('''
        <div style='background: #18181B; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 24px; height: 100%;'>
            <p style='color: #A1A1AA; font-size: 14px; margin: 0; text-align: center; font-family: Inter;'>Awaiting upload...</p>
        </div>
        ''', unsafe_allow_html=True)
    else:
        # Timeline component
        st.markdown('''
        <div style='background: #18181B; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 24px;'>
            <div style='border-left: 2px solid rgba(255,255,255,0.08); padding-left: 16px; margin-left: 8px;'>
                <div style='position: relative; margin-bottom: 24px;'>
                    <div style='position: absolute; left: -25px; top: 4px; width: 10px; height: 10px; border-radius: 50%; background: #22C55E;'></div>
                    <p style='color: #FAFAFA; margin: 0; font-weight: 500; font-size: 14px;'>Resume Uploaded</p>
                    <p style='color: #A1A1AA; margin: 0; font-size: 12px; font-family: Inter;'>Today</p>
                </div>
                <div style='position: relative; margin-bottom: 24px;'>
                    <div style='position: absolute; left: -25px; top: 4px; width: 10px; height: 10px; border-radius: 50%; background: #22C55E;'></div>
                    <p style='color: #FAFAFA; margin: 0; font-weight: 500; font-size: 14px;'>ATS Generated</p>
                    <p style='color: #A1A1AA; margin: 0; font-size: 12px; font-family: Inter;'>Today</p>
                </div>
                <div style='position: relative; margin-bottom: 24px;'>
                    <div style='position: absolute; left: -25px; top: 4px; width: 10px; height: 10px; border-radius: 50%; background: rgba(255,255,255,0.2);'></div>
                    <p style='color: #FAFAFA; margin: 0; font-weight: 500; font-size: 14px;'>Jobs Matched</p>
                    <p style='color: #A1A1AA; margin: 0; font-size: 12px; font-family: Inter;'>Pending view</p>
                </div>
                <div style='position: relative; margin-bottom: 0px;'>
                    <div style='position: absolute; left: -25px; top: 4px; width: 10px; height: 10px; border-radius: 50%; background: rgba(255,255,255,0.2);'></div>
                    <p style='color: #A1A1AA; margin: 0; font-weight: 500; font-size: 14px;'>Interview Generated</p>
                    <p style='color: #52525B; margin: 0; font-size: 12px; font-family: Inter;'>Pending start</p>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
    st.markdown("<h3 style='margin-top: 24px; margin-bottom: 16px; font-size: 18px;'>Quick Actions</h3>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Data & Reset", use_container_width=True, type="secondary"):
        keys_to_clear = ["resume_text", "ats_ml_score", "resume_path", "skills", "health_data", "predicted_role"]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Execution of upload logic:
if uploaded_file and not st.session_state.resume_text:
    with st.status("🧠 Analyzing your resume...", expanded=True) as status:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        
        st.write("📄 Parsing text...")
        text = extract_text_from_pdf(tmp_path)
        from resume_builder import clean_resume_text_bullets
        text = clean_resume_text_bullets(text)
        st.session_state.resume_text = text
        st.session_state.resume_path = tmp_path
        
        st.write("🔍 Extracting Skills...")
        skills = extract_skills(text)
        st.session_state.skills = skills
        
        st.write("📏 Checking Formatting & Health...")
        issues = check_formatting(text, tmp_path)
        st.session_state.issues = issues
        st.session_state.health_data = compute_general_score(text, issues, skills)
        st.session_state.section_scores = compute_section_scores(text)
        
        st.write("🤖 Predicting Job Role...")
        prediction = predict_job_category(text)
        st.session_state.predicted_role = prediction["category"]
        
        st.write("🤖 Analyzing Bullets & Experience...")
        st.session_state.bullet_results = classify_bullets(extract_bullet_points(text))
        st.session_state.yoe = calculate_yoe(text)
        
        st.write("📈 Computing Market Gaps & Alignment...")
        gaps = get_market_skill_gaps(st.session_state.predicted_role, skills)
        st.session_state.market_gaps = gaps
        
        # Resume Health Score
        features = extract_resume_features(text, tmp_path)
        raw_features = {
            "skill_count":        len(st.session_state.skills or []),
            "action_verb_count":  features.get("action_verb_count", 0),
            "metrics_count":      features.get("metrics_count", 0),
            "section_count":      features.get("section_completeness", 0) // 25,
            "formatting_penalty": len([i for i in (st.session_state.issues or []) if i.get("severity") == "high"]),
        }
        health_result = compute_health_score(raw_features)
        base_ats = health_result["total_score"]
        st.session_state.ats_ml_score = {"score": base_ats, "grade": health_result["grade"]}
            
        status.update(label="✅ Analysis Complete!", state="complete", expanded=False)
        st.rerun()
"""

# Find index of the main UI start
start_idx = 0
for i, line in enumerate(lines):
    if line.startswith("# ── Main UI ────────────────────────────────────────────────────────────────────"):
        start_idx = i
        break

if start_idx > 0:
    with open("pages/1_🏠_Dashboard.py", "w") as f:
        f.writelines(lines[:start_idx])
        f.write(new_ui)
