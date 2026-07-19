with open("pages/2__Resume_Analysis.py", "r") as f:
    lines = f.readlines()

new_ui = """
# ── Main UI ────────────────────────────────────────────────────────────────────
# UI Customization styles are injected globally from ui_utils.py

st.markdown("<h1 class='gradient-title' style='font-size: 3rem; margin-bottom: 5px; padding-bottom: 5px;'> Resume Analysis</h1>", unsafe_allow_html=True)

if not st.session_state.resume_text or not st.session_state.ats_ml_score:
    st.markdown('''
    <div style='background: #18181B; border: 1px dashed rgba(255,255,255,0.15); border-radius: 18px; padding: 40px; text-align: center; margin-top: 20px;'>
        <h3 style='color: #FAFAFA; margin-bottom: 8px;'>No Analysis Available</h3>
        <p style='color: #A1A1AA; font-family: Inter; margin-bottom: 24px;'>Please upload a resume on the Dashboard first.</p>
        <a href='/' target='_self' style='text-decoration: none;'><button style='background-color: #22C55E; color: #000000; border: none; border-radius: 99px; font-weight: 700; padding: 10px 24px; cursor: pointer;'>Go to Dashboard</button></a>
    </div>
    ''', unsafe_allow_html=True)
else:
    score = int(st.session_state.ats_ml_score['score'])
    role = st.session_state.get('predicted_role', 'Professional')
    
    # 1. Executive Summary
    st.markdown("<h2 style='margin-top: 30px; margin-bottom: 16px; color: #FAFAFA;'>Executive Summary</h2>", unsafe_allow_html=True)
    st.markdown(f'''
    <div style='background: #18181B; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 24px; margin-bottom: 24px;'>
        <p style='color: #FAFAFA; font-family: Inter; line-height: 1.6; margin: 0;'>
            Your resume was analyzed against top ATS standards for a <strong>{role}</strong> position. 
            Overall, it scored a <strong>{score}/100</strong>, indicating it is {"highly competitive" if score >= 80 else "in need of some improvements" if score >= 60 else "requiring major revisions"}.
        </p>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 2. Keyword Match
        st.markdown("<h3 style='margin-bottom: 12px; color: #FAFAFA;'>Keyword Match</h3>", unsafe_allow_html=True)
        st.markdown('''
        <div style='background: #18181B; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 24px; margin-bottom: 24px; height: 300px; overflow-y: auto;'>
        ''', unsafe_allow_html=True)
        if st.session_state.skills:
            for s in st.session_state.skills[:10]:
                st.markdown(f"<span class='skill-tag skill-match'>✓ {s}</span>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color: #A1A1AA; font-family: Inter;'>No significant keywords found.</p>", unsafe_allow_html=True)
        
        if st.session_state.get("market_gaps") and st.session_state.market_gaps.get("missing_critical"):
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<p style='color: #A1A1AA; font-family: Inter; font-weight: 600; font-size: 14px;'>Missing Crucial Skills:</p>", unsafe_allow_html=True)
            for m in st.session_state.market_gaps["missing_critical"][:5]:
                st.markdown(f"<span class='skill-tag skill-miss'> {m}</span>", unsafe_allow_html=True)
                
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # 3. Formatting & Grammar
        st.markdown("<h3 style='margin-bottom: 12px; color: #FAFAFA;'>Formatting & Grammar</h3>", unsafe_allow_html=True)
        st.markdown('''
        <div style='background: #18181B; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 24px; margin-bottom: 24px; height: 300px; overflow-y: auto;'>
        ''', unsafe_allow_html=True)
        
        issues = st.session_state.get("issues", [])
        if not issues:
            st.markdown("<div style='display: flex; align-items: center; gap: 8px; margin-bottom: 12px;'><span style='color: #22C55E; font-size: 18px;'>✓</span><span style='color: #FAFAFA; font-family: Inter;'>No formatting issues detected.</span></div>", unsafe_allow_html=True)
            st.markdown("<div style='display: flex; align-items: center; gap: 8px;'><span style='color: #22C55E; font-size: 18px;'>✓</span><span style='color: #FAFAFA; font-family: Inter;'>Grammar looks excellent.</span></div>", unsafe_allow_html=True)
        else:
            for issue in issues:
                color = "#EF4444" if issue.get("severity") == "high" else "#F59E0B"
                st.markdown(f"<div style='border-left: 4px solid {color}; padding-left: 12px; margin-bottom: 16px;'><p style='color: #FAFAFA; margin: 0 0 4px 0; font-weight: 600;'>{issue.get('issue', 'Issue')}</p><p style='color: #A1A1AA; margin: 0; font-size: 13px;'>{issue.get('recommendation', '')}</p></div>", unsafe_allow_html=True)
                
        st.markdown("</div>", unsafe_allow_html=True)
        
    # 4. Section-wise Analysis
    st.markdown("<h3 style='margin-top: 16px; margin-bottom: 16px; color: #FAFAFA;'>Section-wise Analysis</h3>", unsafe_allow_html=True)
    if st.session_state.get("section_scores"):
        cols = st.columns(len(st.session_state.section_scores))
        for i, (section, s_score) in enumerate(st.session_state.section_scores.items()):
            with cols[i]:
                color = "#22C55E" if s_score >= 80 else "#F59E0B" if s_score >= 50 else "#EF4444"
                st.markdown(f'''
                <div style='background: #18181B; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 20px; text-align: center;'>
                    <p style='color: #A1A1AA; margin: 0 0 8px 0; font-size: 14px; text-transform: capitalize;'>{section}</p>
                    <h2 style='margin: 0; color: {color}; font-size: 28px;'>{s_score}%</h2>
                </div>
                ''', unsafe_allow_html=True)
    else:
        st.info("Section parsing details unavailable.")
        
    # 5. Action Items
    st.markdown("<h3 style='margin-top: 32px; margin-bottom: 16px; color: #FAFAFA;'>Action Items</h3>", unsafe_allow_html=True)
    st.markdown('''
    <div style='background: #18181B; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 24px;'>
    ''', unsafe_allow_html=True)
    
    actions = []
    if score < 80:
        actions.append("Consider rewriting your summary to include more quantified achievements.")
    if st.session_state.get("market_gaps") and st.session_state.market_gaps.get("missing_critical"):
        actions.append(f"Add missing critical keywords: {', '.join(st.session_state.market_gaps['missing_critical'][:3])}.")
    if st.session_state.get("issues"):
        actions.append("Fix the formatting issues flagged above to ensure standard ATS parsers can read your file.")
    if not actions:
        actions.append("Your resume is highly optimized! Start applying to jobs.")
        
    for idx, act in enumerate(actions, 1):
        st.markdown(f"<div style='display: flex; gap: 12px; margin-bottom: 12px;'><div style='background: #22C55E; color: #000; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;'>{idx}</div><p style='margin: 0; color: #FAFAFA; font-family: Inter; padding-top: 2px;'>{act}</p></div>", unsafe_allow_html=True)
        
    st.markdown("</div>", unsafe_allow_html=True)
"""

start_idx = 0
for i, line in enumerate(lines):
    if line.startswith("# ── Main UI ────────────────────────────────────────────────────────────────────"):
        start_idx = i
        break

if start_idx > 0:
    with open("pages/2__Resume_Analysis.py", "w") as f:
        f.writelines(lines[:start_idx])
        f.write(new_ui)
