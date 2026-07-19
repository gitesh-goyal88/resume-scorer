import streamlit as st
import random
import re




st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    [data-testid="stAppDeployButton"] {display: none;}
    footer {visibility: hidden;}
    .grader-pass { background: #D1FAE5; color: #065F46; padding: 15px; border-radius: 8px; border-left: 4px solid #10B981; }
    .grader-fail { background: #FEE2E2; color: #991B1B; padding: 15px; border-radius: 8px; border-left: 4px solid #EF4444; }
</style>
""", unsafe_allow_html=True)

if "resume_text" not in st.session_state or not st.session_state.resume_text:
    st.warning(" Please upload a resume in the Candidate Portal first to activate the Interview Grader.")
    st.stop()

if not st.session_state.interview_qs:
    st.markdown('''
    <div style='background: #18181B; border: 1px dashed rgba(255,255,255,0.15); border-radius: 18px; padding: 40px; text-align: center; margin-top: 20px;'>
        <h3 style='color: #FAFAFA; margin-bottom: 8px;'>Copilot Locked</h3>
        <p style='color: #A1A1AA; font-family: Inter; margin-bottom: 24px;'>Please generate your Full Report on the Dashboard to unlock tailored interview questions.</p>
        <a href='/' target='_self' style='text-decoration: none;'><button style='background-color: #22C55E; color: #000000; border: none; border-radius: 99px; font-weight: 700; padding: 10px 24px; cursor: pointer;'>Go to Dashboard</button></a>
    </div>
    ''', unsafe_allow_html=True)
else:
    if "active_q" not in st.session_state:
        st.session_state.active_q = random.choice(st.session_state.interview_qs)
        
    st.markdown("<h1 class='gradient-title' style='font-size: 3rem; margin-bottom: 5px; padding-bottom: 5px;'> Interview Copilot</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-heading'>Practice your interview skills. The NLP engine uses the **STAR Method** to verify your answer contains Context, Action Verbs, and Metrics/Results.</p>", unsafe_allow_html=True)
        
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button(" Next Question", use_container_width=True, type="secondary"):
            st.session_state.active_q = random.choice(st.session_state.interview_qs)
            st.rerun()
            
    st.markdown("<br>", unsafe_allow_html=True)
            
    with st.chat_message("ai", avatar=""):
        st.markdown(f"**Here is your question:**\n\n{st.session_state.active_q}")
        
    answer = st.chat_input("Type your answer using the STAR method (Situation, Task, Action, Result)...")
    
    if answer:
        with st.chat_message("user", avatar=""):
            st.markdown(answer)
            
        with st.spinner("Grading response..."):
            if len(answer.split()) < 20:
                with st.chat_message("ai", avatar=""):
                    st.markdown("<div style='background: #3F1D1D; border-left: 4px solid #EF4444; padding: 16px; border-radius: 8px; color: #FAFAFA;'><strong>FAIL (Too Short)</strong><br>Your answer is too short. A good interview response should be at least 3-4 sentences long. Provide more context.</div>", unsafe_allow_html=True)
            else:
                ans_lower = answer.lower()
                
                # STAR DETECTOR LOGIC
                action_verbs = ["developed", "led", "managed", "created", "built", "improved", "designed", "optimized", "spearheaded", "implemented"]
                has_action = any(v in ans_lower for v in action_verbs)
                has_metric = bool(re.search(r'\b\d+%\b|\$\d+|\b\d+\b', answer))
                has_i = " i " in answer.lower() or answer.lower().startswith("i ")
                
                score = 60
                feedback = []
                
                if has_action:
                    score += 15
                    feedback.append(" **Action:** Used strong action verbs.")
                else:
                    feedback.append(" **Action:** Missing strong action verbs (e.g., 'led', 'developed').")
                    
                if has_metric:
                    score += 15
                    feedback.append(" **Result:** Included numbers/metrics to quantify your impact.")
                else:
                    feedback.append(" **Result:** Missing quantifiable metrics (e.g., 'increased by 20%').")
                    
                if has_i:
                    score += 10
                    feedback.append(" **Ownership:** Used 'I' statements to show ownership.")
                else:
                    feedback.append(" **Ownership:** Avoid saying 'we' too much. Use 'I'.")
                
                with st.chat_message("ai", avatar=""):
                    if score >= 85:
                        st.markdown(f"<div style='background: #064E3B; border-left: 4px solid #10B981; padding: 16px; border-radius: 8px; color: #FAFAFA;'><strong>PASS ({score}/100)</strong><br><br>{'<br>'.join(feedback)}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='background: #451A03; border-left: 4px solid #F59E0B; padding: 16px; border-radius: 8px; color: #FAFAFA;'><strong>NEEDS WORK ({score}/100)</strong><br><br>{'<br>'.join(feedback)}<br><br><b>Tip:</b> Try rewriting your answer to include the missing elements above.</div>", unsafe_allow_html=True)
