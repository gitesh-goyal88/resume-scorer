import streamlit as st
import tempfile
import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud
import re
import io

from streamlit_lottie import st_lottie
from analyzer import (
    extract_text_from_pdf, extract_skills, check_formatting,
    compute_general_score, get_market_skill_gaps,
    extract_bullet_points, compute_section_scores, categorize_skills,
    extract_resume_features, calculate_yoe
)
from ml_model import (
    train_all_models,
    predict_job_category,
    classify_bullets,
    compute_health_score
)
from resume_builder import generate_interview_questions, generate_enhanced_pdf
from database import insert_candidate, save_user_resume, get_user_resumes
from job_matcher import get_domain_centroid_score
import shutil

# ── Session state init ─────────────────────────────────────────────────────────
for key in ["resume_text", "resume_path", "skills", "predicted_role", "issues",
            "bullet_results", "market_gaps", "section_scores", "ats_ml_score",
            "interview_qs", "answers", "db_saved", "health_data",
            "edit_name", "edit_summary", "edit_skills_languages", "edit_skills_tools", "edit_skills_soft", "edit_experience", 
            "edit_education", "edit_achievements", "edit_certs_projects",
            "edit_state_initialized"]:
    if key not in st.session_state:
        st.session_state[key] = None

def sanitize_text_field(val, formatter):
    if not val:
        return val
    
    import ast
    import json
    
    # If the value is not a string, format it directly using the formatter
    if not isinstance(val, str):
        try:
            return formatter(val)
        except Exception:
            return str(val)
            
    val_stripped = val.strip()
    
    # Check if the entire field is a python list/dict literal
    if (val_stripped.startswith("[") and val_stripped.endswith("]")) or (val_stripped.startswith("{") and val_stripped.endswith("}")):
        try:
            parsed = ast.literal_eval(val_stripped)
            if parsed:
                return formatter(parsed)
        except Exception:
            try:
                parsed = json.loads(val_stripped)
                if parsed:
                    return formatter(parsed)
            except Exception:
                pass
                
    # Otherwise, clean line-by-line (e.g. if a single bullet line is a bracketed list)
    lines = val.split("\n")
    new_lines = []
    for line in lines:
        stripped = line.strip()
        bullet_marker = ""
        content = stripped
        
        if stripped.startswith("-"):
            bullet_marker = "- "
            content = stripped[1:].strip()
        elif stripped.startswith("•"):
            bullet_marker = "• "
            content = stripped[1:].strip()
        elif stripped.startswith("*"):
            bullet_marker = "* "
            content = stripped[1:].strip()
            
        if content.startswith("[") and content.endswith("]"):
            try:
                parsed = ast.literal_eval(content)
                if isinstance(parsed, list):
                    for item in parsed:
                        new_lines.append(f"{bullet_marker or '- '}{str(item).strip()}")
                    continue
            except Exception:
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, list):
                        for item in parsed:
                            new_lines.append(f"{bullet_marker or '- '}{str(item).strip()}")
                        continue
                except Exception:
                    pass
        new_lines.append(line)
        
    return "\n".join(new_lines)

def sanitize_edit_states():
    from llm_utils import (
        _format_skills_to_text,
        _format_experience_to_text,
        _format_education_to_text,
        _format_projects_to_text,
        _format_achievements_to_text
    )
    
    mapping = {
        "edit_skills_languages": _format_skills_to_text,
        "edit_skills_tools": _format_skills_to_text,
        "edit_skills_soft": _format_skills_to_text,
        "edit_experience": _format_experience_to_text,
        "edit_education": _format_education_to_text,
        "edit_certs_projects": _format_projects_to_text,
        "edit_achievements": _format_achievements_to_text
    }
    
    for key, formatter in mapping.items():
        val = st.session_state.get(key)
        if val:
            sanitized = sanitize_text_field(val, formatter)
            if sanitized != val:
                st.session_state[key] = sanitized

# Run proactive sanitization on every script run
sanitize_edit_states()

def init_structured_lists():
    from resume_builder import _parse_resume_section
    
    # Experience
    if "edit_experience_list" not in st.session_state or st.session_state.edit_experience_list is None:
        if st.session_state.edit_experience:
            st.session_state.edit_experience_list = _parse_resume_section(st.session_state.edit_experience)
        else:
            st.session_state.edit_experience_list = []
            
    # Education
    if "edit_education_list" not in st.session_state or st.session_state.edit_education_list is None:
        if st.session_state.edit_education:
            parsed_edu = _parse_resume_section(st.session_state.edit_education)
            for entry in parsed_edu:
                entry["grades"] = []
                remaining_bullets = []
                for bullet in entry.get("bullets", []):
                    bullet_lower = bullet.lower()
                    if "grade" in bullet_lower or "cgpa" in bullet_lower or "gpa" in bullet_lower or "percentage" in bullet_lower or "class 10" in bullet_lower or "class 12" in bullet_lower:
                        grade_type = "CGPA"
                        if "class 10" in bullet_lower:
                            grade_type = "Class 10 %"
                        elif "class 12" in bullet_lower:
                            grade_type = "Class 12 %"
                        elif "gpa" in bullet_lower:
                            grade_type = "GPA"
                            
                        grade_val = bullet.split(":")[-1].strip() if ":" in bullet else bullet
                        entry["grades"].append({"type": grade_type, "value": grade_val})
                    else:
                        remaining_bullets.append(bullet)
                entry["bullets"] = remaining_bullets
            st.session_state.edit_education_list = parsed_edu
        else:
            st.session_state.edit_education_list = []
            
    # Projects
    if "edit_projects_list" not in st.session_state or st.session_state.edit_projects_list is None:
        if st.session_state.edit_certs_projects:
            st.session_state.edit_projects_list = _parse_resume_section(st.session_state.edit_certs_projects)
        else:
            st.session_state.edit_projects_list = []
            
    # Achievements
    if "edit_achievements_list" not in st.session_state or st.session_state.edit_achievements_list is None:
        if st.session_state.edit_achievements:
            ach_parsed = _parse_resume_section(st.session_state.edit_achievements)
            bullets = []
            for entry in ach_parsed:
                bullets.extend(entry.get("bullets", []))
            st.session_state.edit_achievements_list = bullets
        else:
            st.session_state.edit_achievements_list = []
            
    # Skills
    if "edit_skills_languages_list" not in st.session_state or st.session_state.edit_skills_languages_list is None:
        st.session_state.edit_skills_languages_list = [s.strip() for s in (st.session_state.edit_skills_languages or "").split(",") if s.strip()]
        
    if "edit_skills_tools_list" not in st.session_state or st.session_state.edit_skills_tools_list is None:
        st.session_state.edit_skills_tools_list = [s.strip() for s in (st.session_state.edit_skills_tools or "").split(",") if s.strip()]
        
    if "edit_skills_soft_list" not in st.session_state or st.session_state.edit_skills_soft_list is None:
        st.session_state.edit_skills_soft_list = [s.strip() for s in (st.session_state.edit_skills_soft or "").split(",") if s.strip()]

def sync_lists_to_text():
    from llm_utils import (
        _format_experience_to_text,
        _format_projects_to_text
    )
    
    if "edit_experience_list" in st.session_state and st.session_state.edit_experience_list is not None:
        st.session_state.edit_experience = _format_experience_to_text(st.session_state.edit_experience_list)
        
    if "edit_education_list" in st.session_state and st.session_state.edit_education_list is not None:
        edu_entries_formatted = []
        for entry in st.session_state.edit_education_list:
            bullets = list(entry.get("bullets", []))
            for g in entry.get("grades", []):
                bullets.append(f"Grade ({g['type']}): {g['value']}")
            copy_entry = dict(entry)
            copy_entry["bullets"] = bullets
            edu_entries_formatted.append(copy_entry)
            
        from llm_utils import _format_education_to_text
        st.session_state.edit_education = _format_education_to_text(edu_entries_formatted)
        
    if "edit_projects_list" in st.session_state and st.session_state.edit_projects_list is not None:
        st.session_state.edit_certs_projects = _format_projects_to_text(st.session_state.edit_projects_list)
        
    if "edit_achievements_list" in st.session_state and st.session_state.edit_achievements_list is not None:
        st.session_state.edit_achievements = "\n".join(f"- {a}" for a in st.session_state.edit_achievements_list if a)
        
    if "edit_skills_languages_list" in st.session_state and st.session_state.edit_skills_languages_list is not None:
        st.session_state.edit_skills_languages = ", ".join(st.session_state.edit_skills_languages_list)
    if "edit_skills_tools_list" in st.session_state and st.session_state.edit_skills_tools_list is not None:
        st.session_state.edit_skills_tools = ", ".join(st.session_state.edit_skills_tools_list)
    if "edit_skills_soft_list" in st.session_state and st.session_state.edit_skills_soft_list is not None:
        st.session_state.edit_skills_soft = ", ".join(st.session_state.edit_skills_soft_list)

def enhance_single_project(project_entry):
    from llm_utils import call_groq_api
    import json
    bullets_str = "\n".join(f"- {b}" for b in project_entry.get("bullets", []))
    prompt = f"""You are a professional resume writer and ATS optimization expert. Enhance this specific project entry to be highly professional and ATS-optimized.
Use active verbs and quantify results where possible. Follow the Google X-Y-Z formula for the description bullets.

PROJECT DETAILS:
Title/Heading: {project_entry.get('title', '')}
Subtitle/Role: {project_entry.get('subtitle', '')}
Current Description Bullets:
{bullets_str}

Return ONLY a JSON object in this format:
{{
  "title": "Enhanced Title",
  "subtitle": "Enhanced Subtitle/Role",
  "bullets": [
    "Enhanced bullet 1",
    "Enhanced bullet 2"
  ]
}}
Do NOT output any markdown code blocks (```json or ```) or explanations outside the JSON. Respond with the raw JSON string only.
"""
    system_prompt = "You are a professional resume writer. Respond with raw JSON only."
    try:
        response_text = call_groq_api(prompt, system_prompt)
        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?\n", "", response_text)
            response_text = re.sub(r"\n```$", "", response_text)
            response_text = response_text.strip()
        data = json.loads(response_text)
        return data
    except Exception as e:
        st.error(f"Error enhancing project: {e}")
        return None

def enhance_single_achievement(achievement_text):
    from llm_utils import call_groq_api
    import json
    prompt = f"""You are a professional resume writer and ATS optimization expert. Enhance this single achievement statement to be highly professional, impactful, and clear.
Highlight honors, academic standing, or competition rankings. Keep it to a single concise sentence.

ACHIEVEMENT STATEMENT:
{achievement_text}

Return ONLY a JSON object in this format:
{{
  "enhanced_text": "Enhanced achievement statement"
}}
Do NOT output any markdown code blocks (```json or ```) or explanations outside the JSON. Respond with the raw JSON string only.
"""
    system_prompt = "You are a professional resume writer. Respond with raw JSON only."
    try:
        response_text = call_groq_api(prompt, system_prompt)
        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?\n", "", response_text)
            response_text = re.sub(r"\n```$", "", response_text)
            response_text = response_text.strip()
        data = json.loads(response_text)
        return data.get("enhanced_text", achievement_text)
    except Exception as e:
        st.error(f"Error enhancing achievement: {e}")
        return None

def render_resume_editor():
    import json
    import base64
    st.header("✍️ Interactive Resume Editor & AI Templates")
    st.markdown("Modify your resume details below. Any edits or styling changes will automatically update the PDF preview on the right.")
    
    role = st.session_state.predicted_role or "Professional"
    
    # Initialize structured lists from plain text area states
    init_structured_lists()
    
    # Helper to render PDF pages as styled images to bypass Chrome security blocks and maintain proportions
    def display_pdf_as_images(pdf_path):
        import fitz
        import base64
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                base64_img = base64.b64encode(img_bytes).decode('utf-8')
                st.markdown(
                    f'<div style="display: flex; justify-content: center; margin-bottom: 20px;">'
                    f'<img src="data:image/png;base64,{base64_img}" style="width: 100%; max-width: 600px; border: 1px solid #cbd5e1; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);" />'
                    f'</div>',
                    unsafe_allow_html=True
                )
        except Exception as e:
            st.error(f"Could not render PDF preview: {e}")

    # Divide screen into Edit Controls (Left) and Live PDF Preview (Right)
    col_edit, col_preview = st.columns([1.1, 0.9])
    
    with col_edit:
        st.subheader("📝 Edit Content")
        
        col_name, col_role = st.columns(2)
        with col_name:
            st.session_state.edit_name = st.text_input("Full Name:", value=st.session_state.edit_name or "")
        with col_role:
            st.session_state.predicted_role = st.text_input("Target Role / Title:", value=role)
            
        st.session_state.edit_summary = st.text_area("Professional Summary:", value=st.session_state.edit_summary or "", height=100)
        
        # 1. Expander: Skills
        with st.expander("🛠️ Skills", expanded=True):
            st.markdown("**Languages**")
            for idx, lang in enumerate(list(st.session_state.edit_skills_languages_list)):
                col_val, col_del = st.columns([0.85, 0.15])
                with col_val:
                    st.session_state.edit_skills_languages_list[idx] = st.text_input(f"Language #{idx+1}", value=lang, key=f"lang_{idx}", label_visibility="collapsed")
                with col_del:
                    if st.button("🗑️", key=f"del_lang_{idx}"):
                        st.session_state.edit_skills_languages_list.pop(idx)
                        st.rerun()
            if st.button("➕ Add Language", key="add_lang"):
                st.session_state.edit_skills_languages_list.append("")
                st.rerun()
                
            st.markdown("**Tools & Technologies**")
            for idx, tool in enumerate(list(st.session_state.edit_skills_tools_list)):
                col_val, col_del = st.columns([0.85, 0.15])
                with col_val:
                    st.session_state.edit_skills_tools_list[idx] = st.text_input(f"Tool #{idx+1}", value=tool, key=f"tool_{idx}", label_visibility="collapsed")
                with col_del:
                    if st.button("🗑️", key=f"del_tool_{idx}"):
                        st.session_state.edit_skills_tools_list.pop(idx)
                        st.rerun()
            if st.button("➕ Add Tool / Tech", key="add_tool"):
                st.session_state.edit_skills_tools_list.append("")
                st.rerun()
                
            st.markdown("**Soft Skills**")
            for idx, soft in enumerate(list(st.session_state.edit_skills_soft_list)):
                col_val, col_del = st.columns([0.85, 0.15])
                with col_val:
                    st.session_state.edit_skills_soft_list[idx] = st.text_input(f"Soft Skill #{idx+1}", value=soft, key=f"soft_{idx}", label_visibility="collapsed")
                with col_del:
                    if st.button("🗑️", key=f"del_soft_{idx}"):
                        st.session_state.edit_skills_soft_list.pop(idx)
                        st.rerun()
            if st.button("➕ Add Soft Skill", key="add_soft"):
                st.session_state.edit_skills_soft_list.append("")
                st.rerun()

        # 2. Expander: Work Experience
        with st.expander("💼 Work Experience", expanded=False):
            for idx, entry in enumerate(list(st.session_state.edit_experience_list)):
                st.markdown(f"---")
                col_title, col_del = st.columns([0.85, 0.15])
                with col_title:
                    st.markdown(f"**Role #{idx+1}: {entry.get('title') or 'New Role'}**")
                with col_del:
                    if st.button("🗑️ Delete", key=f"del_exp_{idx}"):
                        st.session_state.edit_experience_list.pop(idx)
                        st.rerun()
                        
                col1, col2 = st.columns(2)
                with col1:
                    st.session_state.edit_experience_list[idx]["title"] = st.text_input("Company / Organization:", value=entry.get("title", ""), key=f"exp_{idx}_title")
                    st.session_state.edit_experience_list[idx]["location"] = st.text_input("Location:", value=entry.get("location", ""), key=f"exp_{idx}_location")
                with col2:
                    st.session_state.edit_experience_list[idx]["subtitle"] = st.text_input("Position / Title:", value=entry.get("subtitle", ""), key=f"exp_{idx}_subtitle")
                    st.session_state.edit_experience_list[idx]["dates"] = st.text_input("Dates / Duration:", value=entry.get("dates", ""), key=f"exp_{idx}_dates")
                    
                bullets_text = "\n".join(entry.get("bullets", []))
                new_bullets_text = st.text_area("Description (One bullet point per line):", value=bullets_text, key=f"exp_{idx}_bullets", height=120)
                st.session_state.edit_experience_list[idx]["bullets"] = [b.strip() for b in new_bullets_text.split("\n") if b.strip()]
                
            if st.button("➕ Add Work Experience", key="add_exp"):
                st.session_state.edit_experience_list.append({
                    "title": "",
                    "subtitle": "",
                    "location": "",
                    "dates": "",
                    "bullets": [""]
                })
                st.rerun()

        # 3. Expander: Education
        with st.expander("🎓 Education", expanded=False):
            for idx, entry in enumerate(list(st.session_state.edit_education_list)):
                st.markdown(f"---")
                col_title, col_del = st.columns([0.85, 0.15])
                with col_title:
                    st.markdown(f"**Education #{idx+1}: {entry.get('title') or 'New Institution'}**")
                with col_del:
                    if st.button("🗑️ Delete", key=f"del_edu_{idx}"):
                        st.session_state.edit_education_list.pop(idx)
                        st.rerun()
                        
                col1, col2 = st.columns(2)
                with col1:
                    st.session_state.edit_education_list[idx]["title"] = st.text_input("Institution / School / College:", value=entry.get("title", ""), key=f"edu_{idx}_title")
                    st.session_state.edit_education_list[idx]["location"] = st.text_input("Location:", value=entry.get("location", ""), key=f"edu_{idx}_location")
                with col2:
                    st.session_state.edit_education_list[idx]["subtitle"] = st.text_input("Degree / Course:", value=entry.get("subtitle", ""), key=f"edu_{idx}_subtitle")
                    st.session_state.edit_education_list[idx]["dates"] = st.text_input("Dates / Years (e.g. 2018 - 2022):", value=entry.get("dates", ""), key=f"edu_{idx}_dates")
                    
                st.markdown("**Grades & Academic Standing:**")
                grades = entry.get("grades", [])
                for g_idx, g in enumerate(list(grades)):
                    col_type, col_val, col_gdel = st.columns([0.5, 0.4, 0.1])
                    with col_type:
                        grade_types = ["CGPA", "Class 10 %", "Class 12 %", "GPA", "Percentage"]
                        default_type_idx = grade_types.index(g["type"]) if g["type"] in grade_types else 0
                        selected_type = st.selectbox("Grade Type:", grade_types, index=default_type_idx, key=f"edu_{idx}_gtype_{g_idx}")
                        st.session_state.edit_education_list[idx]["grades"][g_idx]["type"] = selected_type
                    with col_val:
                        st.session_state.edit_education_list[idx]["grades"][g_idx]["value"] = st.text_input("Value / Score:", value=g["value"], key=f"edu_{idx}_gval_{g_idx}")
                    with col_gdel:
                        st.write("")
                        if st.button("🗑️", key=f"edu_{idx}_gdel_{g_idx}"):
                            st.session_state.edit_education_list[idx]["grades"].pop(g_idx)
                            st.rerun()
                if st.button("➕ Add Grade / Score", key=f"edu_{idx}_gadd"):
                    if "grades" not in st.session_state.edit_education_list[idx]:
                        st.session_state.edit_education_list[idx]["grades"] = []
                    st.session_state.edit_education_list[idx]["grades"].append({"type": "CGPA", "value": ""})
                    st.rerun()
                    
                bullets_text = "\n".join(entry.get("bullets", []))
                new_bullets_text = st.text_area("Other details/honors (One per line):", value=bullets_text, key=f"edu_{idx}_bullets", height=80)
                st.session_state.edit_education_list[idx]["bullets"] = [b.strip() for b in new_bullets_text.split("\n") if b.strip()]
                
            if st.button("➕ Add Education", key="add_edu"):
                st.session_state.edit_education_list.append({
                    "title": "",
                    "subtitle": "",
                    "location": "",
                    "dates": "",
                    "grades": [],
                    "bullets": []
                })
                st.rerun()

        # 4. Expander: Projects & Certifications
        with st.expander("🚀 Certifications & Projects", expanded=False):
            for idx, entry in enumerate(list(st.session_state.edit_projects_list)):
                st.markdown(f"---")
                col_title, col_del = st.columns([0.85, 0.15])
                with col_title:
                    st.markdown(f"**Project #{idx+1}: {entry.get('title') or 'New Project'}**")
                with col_del:
                    if st.button("🗑️ Delete", key=f"del_proj_{idx}"):
                        st.session_state.edit_projects_list.pop(idx)
                        st.rerun()
                        
                col1, col2 = st.columns(2)
                with col1:
                    st.session_state.edit_projects_list[idx]["title"] = st.text_input("Project Title:", value=entry.get("title", ""), key=f"proj_{idx}_title")
                    st.session_state.edit_projects_list[idx]["location"] = st.text_input("Link / URL:", value=entry.get("location", ""), key=f"proj_{idx}_location")
                with col2:
                    st.session_state.edit_projects_list[idx]["subtitle"] = st.text_input("Role / Technologies:", value=entry.get("subtitle", ""), key=f"proj_{idx}_subtitle")
                    st.session_state.edit_projects_list[idx]["dates"] = st.text_input("Dates / Duration:", value=entry.get("dates", ""), key=f"proj_{idx}_dates")
                    
                bullets_text = "\n".join(entry.get("bullets", []))
                new_bullets_text = st.text_area("Project Description Bullets (One per line):", value=bullets_text, key=f"proj_{idx}_bullets", height=120)
                st.session_state.edit_projects_list[idx]["bullets"] = [b.strip() for b in new_bullets_text.split("\n") if b.strip()]
                
                # Single Project AI Enhancement Button
                if st.button("🤖 Enhance this Project with AI", key=f"proj_{idx}_ai"):
                    with st.spinner("Optimizing project using Groq AI..."):
                        enhanced = enhance_single_project(st.session_state.edit_projects_list[idx])
                        if enhanced:
                            st.session_state.edit_projects_list[idx]["title"] = enhanced.get("title", st.session_state.edit_projects_list[idx]["title"])
                            st.session_state.edit_projects_list[idx]["subtitle"] = enhanced.get("subtitle", st.session_state.edit_projects_list[idx]["subtitle"])
                            st.session_state.edit_projects_list[idx]["bullets"] = enhanced.get("bullets", st.session_state.edit_projects_list[idx]["bullets"])
                            st.success("✅ Project successfully enhanced!")
                            st.rerun()
                            
            if st.button("➕ Add Project", key="add_proj"):
                st.session_state.edit_projects_list.append({
                    "title": "",
                    "subtitle": "",
                    "location": "",
                    "dates": "",
                    "bullets": [""]
                })
                st.rerun()

        # 5. Expander: Achievements
        with st.expander("🏆 Achievements", expanded=False):
            for idx, bullet in enumerate(list(st.session_state.edit_achievements_list)):
                col_val, col_ai, col_del = st.columns([0.7, 0.2, 0.1])
                with col_val:
                    st.session_state.edit_achievements_list[idx] = st.text_input(f"Achievement #{idx+1}", value=bullet, key=f"ach_{idx}", label_visibility="collapsed")
                with col_ai:
                    if st.button("🤖 Enhance", key=f"ach_{idx}_ai"):
                        with st.spinner("Enhancing achievement..."):
                            enhanced = enhance_single_achievement(st.session_state.edit_achievements_list[idx])
                            if enhanced:
                                st.session_state.edit_achievements_list[idx] = enhanced
                                st.success("✅ Enhanced!")
                                st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"ach_{idx}_del"):
                        st.session_state.edit_achievements_list.pop(idx)
                        st.rerun()
            if st.button("➕ Add Achievement", key="add_ach"):
                st.session_state.edit_achievements_list.append("")
                st.rerun()

        # AI Enhance Section
        st.markdown("---")
        st.subheader("🤖 AI Resume Enhancement")
        
        st.markdown("Select which sections you want the AI to enhance:")
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            enhance_summary = st.checkbox("Professional Summary", value=True, key="opt_summary")
            enhance_skills = st.checkbox("Skills (Languages, Tools, Soft Skills)", value=True, key="opt_skills")
            enhance_experience = st.checkbox("Work Experience", value=True, key="opt_experience")
        with col_opt2:
            enhance_education = st.checkbox("Education", value=True, key="opt_education")
            enhance_projects = st.checkbox("Certifications & Projects", value=True, key="opt_projects")
            enhance_achievements = st.checkbox("Achievements", value=True, key="opt_achievements")
            
        selected_sections = []
        if enhance_summary: selected_sections.append("summary")
        if enhance_skills: selected_sections.extend(["skills_languages", "skills_tools", "skills_soft"])
        if enhance_experience: selected_sections.append("experience")
        if enhance_education: selected_sections.append("education")
        if enhance_projects: selected_sections.append("certs_projects")
        if enhance_achievements: selected_sections.append("achievements")

        st.markdown("💡 **Optional Metrics Context** (Provide answers below to help the AI add quantifiable outcomes):")
        q_metrics = st.text_input("1. Metrics & Outcomes: Did you improve speed, reduce cost, or increase efficiency? (e.g. 'Reduced latency by 35%')", value="", key="q_metrics")
        q_scale = st.text_input("2. Scale & Volume: How many users, servers, or data volume did you work with? (e.g. '15k daily active users')", value="", key="q_scale")
        q_tech = st.text_input("3. Tech Stack Detail: What specific languages, tools, or libraries did you use? (e.g. 'Docker, FastAPI, React')", value="", key="q_tech")
        q_ownership = st.text_input("4. Ownership & Scope: What was your specific contribution or team size? (e.g. 'Led a team of 4 to design database schema')", value="", key="q_ownership")

        if st.button("🚀 Enhance with Groq AI", type="secondary", use_container_width=True):
            if not selected_sections:
                st.warning("⚠️ Please select at least one section to enhance!")
            else:
                with st.spinner("Analyzing feedback & generating improvements with Groq Llama-3..."):
                    # Gather weak bullets and feedback points
                    feedback_bullets = []
                    if st.session_state.bullet_results:
                        for b in st.session_state.bullet_results:
                            if b.get("label") == "Weak":
                                feedback_bullets.append(f"- Bullet: \"{b['text']}\" -> Feedback: missing metrics or strong verbs.")
                    
                    feedback_issues = []
                    if st.session_state.issues:
                        for issue in st.session_state.issues:
                            feedback_issues.append(f"- Formatting Issue: {issue.get('issue')}")
                    
                    feedback_str = "\n".join(feedback_bullets + feedback_issues)
                    
                    sections_to_enhance_str = ", ".join(selected_sections)
                    
                    additional_context_parts = []
                    if q_metrics.strip(): additional_context_parts.append(f"- Metrics/Outcomes: {q_metrics.strip()}")
                    if q_scale.strip(): additional_context_parts.append(f"- Scale/Volume: {q_scale.strip()}")
                    if q_tech.strip(): additional_context_parts.append(f"- Tech Stack: {q_tech.strip()}")
                    if q_ownership.strip(): additional_context_parts.append(f"- Ownership/Scope: {q_ownership.strip()}")
                    additional_context_str = "\n".join(additional_context_parts) if additional_context_parts else "None"
                    
                    prompt = f"""You are a professional resume writer and ATS optimization expert. Your task is to enhance the selected sections of the candidate's resume to make them highly impactful, professional, and ATS-friendly.

CRITICAL TRUTHFULNESS RULES - NEVER VIOLATE:
1. DO NOT add any skill, tool, technology, or certification that is not explicitly mentioned in the original resume.
2. DO NOT invent numeric achievements (e.g., "increased sales by 30%") unless they exist in the original text. You may rephrase existing metrics to be more impact-driven, but never fabricate new numbers.
3. DO NOT add company names, product names, or technical terms not supported by the candidate's actual experience.
4. DO NOT upgrade experience level (e.g., "Junior Software Engineer" -> "Senior Software Engineer").
5. DO NOT extend employment dates or change timelines. Copy date ranges exactly as they appear, including months.
6. Preserve factual accuracy - only use information provided by the candidate.
7. NEVER remove existing skills, certifications, languages, or awards. You may reorder by relevance, but every original item must remain.

SECTIONS TO ENHANCE:
{sections_to_enhance_str}

FEEDBACK AND ISSUES TO RESOLVE (if any):
{feedback_str}

CANDIDATE'S ADDITIONAL CONTEXT (incorporate this context to add quantifiable metrics and impact):
{additional_context_str}

ORIGINAL RESUME DATA:
- Name: {st.session_state.edit_name}
- Target Role: {st.session_state.predicted_role}
- Summary: {st.session_state.edit_summary}
- Skills (Languages): {st.session_state.edit_skills_languages}
- Skills (Tools & Tech): {st.session_state.edit_skills_tools}
- Skills (Soft Skills): {st.session_state.edit_skills_soft}
- Work Experience: {st.session_state.edit_experience}
- Education: {st.session_state.edit_education}
- Certifications & Projects: {st.session_state.edit_certs_projects}
- Achievements: {st.session_state.edit_achievements}

ENHANCEMENT INSTRUCTIONS FOR SECTIONS:
- summary: Rewrite to be a concise, powerful professional summary (2-3 sentences) emphasizing the candidate's core expertise and target role. Do not use generic buzzwords.
- skills_languages / skills_tools / skills_soft: Keep them clean, industry-standard, and well-organized.
- experience: Rewrite bullet points using the Google X-Y-Z formula (Accomplished [X] as measured by [Y], by doing [Z]). Start with strong action verbs. Highlight responsibilities, tools used, and outcomes. Keep all original dates, company names, and locations unchanged.
- education: Clean up formatting, preserve degrees, institutions, and years.
- certs_projects: Enhance project descriptions and bullets to clearly show technical implementation details and results.
- achievements: Rephrase achievements to highlight honors, academic performance, or competition rankings clearly.

OUTPUT FORMAT:
Return ONLY a valid JSON object containing all the keys listed below. For any section NOT selected for enhancement, you MUST copy the original value exactly as it is without any changes.

Expected JSON output format:
{{
  "name": "{st.session_state.edit_name}",
  "summary": "...",
  "skills_languages": "...",
  "skills_tools": "...",
  "skills_soft": "...",
  "experience": "...",
  "education": "...",
  "certs_projects": "...",
  "achievements": "..."
}}
Do NOT output any markdown code block backticks (```json or ```), styling, or explanations outside the JSON. Respond with the raw JSON string only.
"""
                    system_prompt = "You are a professional resume writer. Respond with raw JSON only. Do not include markdown code block backticks (```json or ```)."
                    
                    from llm_utils import call_groq_api
                    response_text = call_groq_api(prompt, system_prompt)
                    
                    # Clean response text in case markdown block wrapper is outputted anyway
                    if response_text.startswith("```"):
                        response_text = re.sub(r"^```(?:json)?\n", "", response_text)
                        response_text = re.sub(r"\n```$", "", response_text)
                        response_text = response_text.strip()
                        
                    try:
                        improved_data = json.loads(response_text)
                        from llm_utils import (
                            _format_skills_to_text,
                            _format_experience_to_text,
                            _format_education_to_text,
                            _format_projects_to_text,
                            _format_achievements_to_text
                        )
                        st.session_state.edit_name = str(improved_data.get("name", st.session_state.edit_name)).strip()
                        
                        if enhance_summary:
                            st.session_state.edit_summary = str(improved_data.get("summary", st.session_state.edit_summary)).strip()
                        if enhance_skills:
                            st.session_state.edit_skills_languages = _format_skills_to_text(improved_data.get("skills_languages", st.session_state.edit_skills_languages))
                            st.session_state.edit_skills_tools = _format_skills_to_text(improved_data.get("skills_tools", st.session_state.edit_skills_tools))
                            st.session_state.edit_skills_soft = _format_skills_to_text(improved_data.get("skills_soft", st.session_state.edit_skills_soft))
                        if enhance_experience:
                            st.session_state.edit_experience = _format_experience_to_text(improved_data.get("experience", st.session_state.edit_experience))
                        if enhance_education:
                            st.session_state.edit_education = _format_education_to_text(improved_data.get("education", st.session_state.edit_education))
                        if enhance_projects:
                            st.session_state.edit_certs_projects = _format_projects_to_text(improved_data.get("certs_projects", st.session_state.edit_certs_projects))
                        if enhance_achievements:
                            st.session_state.edit_achievements = _format_achievements_to_text(improved_data.get("achievements", st.session_state.edit_achievements))
                            
                        # Clear old lists so they refresh on the next run
                        for list_key in [
                            "edit_experience_list", "edit_education_list", "edit_projects_list",
                            "edit_achievements_list", "edit_skills_languages_list",
                            "edit_skills_tools_list", "edit_skills_soft_list"
                        ]:
                            if list_key in st.session_state:
                                del st.session_state[list_key]
                                
                        st.success("✅ Selected resume sections successfully enhanced by Groq AI! Review the changes below.")
                        st.rerun()
                    except Exception as e:
                        st.error("Failed to parse AI response. The response was:")
                        st.code(response_text)
                    
        # PDF Layout & Styling Panel
        st.markdown("---")
        st.subheader("🎨 PDF Styling & Templates")
        with st.expander("PDF Formatting Options", expanded=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                pdf_template = st.selectbox("Template Layout Style", ["Clean", "Modern Two-Column", "Vivid", "Classic"], index=0)
                pdf_font = st.selectbox("Font Family", ["Helvetica", "Times", "Courier"], index=0)
                pdf_color = st.selectbox("Color Theme", ["Dark Blue", "Black", "Green", "Crimson Red", "Slate Grey"], index=0)
            with col_f2:
                pdf_page_size = st.selectbox("Page Size", ["A4", "Letter"], index=0)
                pdf_font_size = st.slider("Base Font Size (pt)", min_value=8, max_value=14, value=10, step=1)
                pdf_margin = st.slider("Page Margin (mm)", min_value=10, max_value=30, value=15, step=5)
                
        # Sync structured lists back to plain text state variables
        sync_lists_to_text()

    with col_preview:
        st.subheader("📄 Live PDF Preview")
        
        # Compile PDF on page load/interaction
        with st.spinner("Updating PDF preview..."):
            from resume_builder import generate_enhanced_pdf_direct
            output_path = os.path.join(tempfile.gettempdir(), "live_preview_styled_resume.pdf")
            try:
                generate_enhanced_pdf_direct(
                    name=st.session_state.edit_name,
                    summary=st.session_state.edit_summary,
                    skills_text="",
                    experience=st.session_state.edit_experience,
                    education=st.session_state.edit_education,
                    achievements=st.session_state.edit_achievements,
                    certs_projects=st.session_state.edit_certs_projects,
                    output_path=output_path,
                    font_family=pdf_font,
                    base_font_size=pdf_font_size,
                    margin=pdf_margin,
                    primary_color_name=pdf_color,
                    page_size=pdf_page_size,
                    template_style=pdf_template,
                    predicted_role=st.session_state.predicted_role,
                    original_text=st.session_state.resume_text,
                    skills_languages=st.session_state.edit_skills_languages,
                    skills_tools=st.session_state.edit_skills_tools,
                    skills_soft=st.session_state.edit_skills_soft
                )
                
                # Show PDF as images instead of an iframe to bypass Chrome security blocks
                display_pdf_as_images(output_path)
                
                # Download button below the preview
                st.markdown(" ")
                with open(output_path, "rb") as f:
                    st.download_button("📥 Download Styled PDF Resume", data=f.read(), file_name="enhanced_styled_resume.pdf", mime="application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"Failed to generate live preview: {e}")
                st.exception(e)

def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except:
        return None

lottie_ai = load_lottieurl("https://lottie.host/804d9c73-ec14-41e9-911b-c662a5bafbe5/2iPZJ29Npe.json")

# ── Chart Functions (LIGHT MODE) ──────────────────────────────────────────────
def create_gauge_chart(score, title="Score"):
    fig, ax = plt.subplots(figsize=(4, 2.5), subplot_kw={'projection': 'polar'})
    fig.patch.set_facecolor('white')
    angle = np.pi * (1 - score / 100)
    theta_bg = np.linspace(0, np.pi, 100)
    ax.fill_between(theta_bg, 0.6, 1.0, color='#E2E8F0', alpha=1.0)
    theta_score = np.linspace(np.pi, angle, 100)
    color = '#10B981' if score >= 70 else '#F59E0B' if score >= 40 else '#EF4444'
    ax.fill_between(theta_score, 0.6, 1.0, color=color, alpha=1.0)
    ax.set_ylim(0, 1.2)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.axis('off')
    ax.text(np.pi/2, 0.2, f"{score}", ha='center', va='center', fontsize=28, fontweight='bold', color=color)
    ax.text(np.pi/2, -0.15, title, ha='center', va='center', fontsize=12, color='#1E293B', fontweight='bold')
    plt.tight_layout()
    return fig

def create_radar_chart(skill_categories):
    categories = list(skill_categories.keys())
    values = [skill_categories[c]["score"] for c in categories]
    N = len(categories)
    if N == 0: return plt.subplots(figsize=(4,4))[0]
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    values += values[:1]
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.plot(angles, values, 'o-', linewidth=2, color='#2563EB')
    ax.fill(angles, values, alpha=0.2, color='#2563EB')
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, size=10, color='#1E293B')
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(['25', '50', '75', '100'], size=7, color='#64748B')
    ax.spines['polar'].set_color('#E2E8F0')
    ax.grid(color='#E2E8F0', linewidth=1)
    plt.tight_layout()
    return fig

def create_section_bar_chart(section_scores):
    sections = list(section_scores.keys())
    scores = list(section_scores.values())
    fig, ax = plt.subplots(figsize=(5, 3))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    colors = ['#10B981' if s >= 70 else '#F59E0B' if s >= 40 else '#EF4444' for s in scores]
    bars = ax.barh(sections, scores, color=colors, height=0.5)
    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2, f'{score}%', va='center', ha='left', fontsize=10, color='#1E293B', fontweight='bold')
    ax.set_xlim(0, 110)
    ax.tick_params(colors='#1E293B', labelsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#E2E8F0')
    ax.spines['left'].set_color('#E2E8F0')
    plt.tight_layout()
    return fig

def create_word_cloud(text):
    stopwords = set(["and", "the", "to", "of", "in", "for", "with", "a", "on", "by", "an", "as", "at", "from"])
    wordcloud = WordCloud(width=800, height=400, background_color='white', colormap='Blues', stopwords=stopwords).generate(text)
    fig, ax = plt.subplots(figsize=(6, 3))
    fig.patch.set_facecolor('white')
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    plt.tight_layout()
    return fig

# ── Helper: Action Verbs & Salary ──────────────────────────────────────────────
def suggest_action_verbs(text):
    passive = ["worked on", "helped", "assisted", "was responsible for", "did", "made"]
    suggestions = []
    text_lower = text.lower()
    for p in passive:
        if p in text_lower:
            suggestions.append(p)
    return suggestions

def estimate_salary(role, ats_score):
    base = 60000
    if "Engineer" in role or "Developer" in role or "Data" in role:
        base = 80000
    elif "Manager" in role or "Lead" in role:
        base = 100000
    
    # Scale based on ATS score (proxy for quality/experience)
    multiplier = (ats_score / 100) + 0.5 # 0.5 to 1.5 range
    low = int((base * multiplier) / 1000) * 1000
    high = int((base * multiplier * 1.3) / 1000) * 1000
    return f"${low:,} - ${high:,}"

# ── Main UI ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.skill-tag { display: inline-block; padding: 4px 10px; border-radius: 12px; margin: 4px; font-size: 13px; font-weight: 500; }
.skill-match { background: #D1FAE5; color: #065F46; border: 1px solid #10B981; }
.skill-miss { background: #FEE2E2; color: #991B1B; border: 1px solid #EF4444; }
.bullet-card { padding: 10px; margin-bottom: 8px; background: #FFFFFF; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #E2E8F0; }
.b-strong { border-left: 4px solid #10B981; }
.b-weak { border-left: 4px solid #EF4444; }
.b-sugg { color: #2563EB; font-weight: bold; font-size: 13px;}
.info-card { background: #F0F9FF; border: 1px solid #BAE6FD; padding: 16px; border-radius: 8px; margin-bottom: 16px;}
</style>
""", unsafe_allow_html=True)

st.title("📄 Candidate Portal")
st.markdown("Upload your resume to get your **Full Report**, Salary Estimate, and tailored LinkedIn bio.")

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader("Drop your resume (PDF)", type=["pdf"])
with col2:
    if lottie_ai: st_lottie(lottie_ai, height=120, key="ai_brain")

if st.session_state.resume_text:
    if st.button("🗑️ Clear & Upload New Resume", type="secondary"):
        keys_to_clear = [
            "resume_text", "resume_path", "skills", "issues", "health_data", 
            "predicted_role", "bullet_results", "market_gaps", "ats_ml_score", 
            "section_scores", "yoe", "interview_qs", "edit_state_initialized",
            "edit_name", "edit_summary", "edit_skills_languages", "edit_skills_tools", "edit_skills_soft",
            "edit_experience", "edit_education", "edit_achievements", "edit_certs_projects",
            "edit_experience_list", "edit_education_list", "edit_projects_list",
            "edit_achievements_list", "edit_skills_languages_list", "edit_skills_tools_list", "edit_skills_soft_list"
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

if uploaded_file and not st.session_state.resume_text:
    if st.button("Generate Full Report", use_container_width=True, type="primary"):
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
                
            status.update(label="✅ Full Report Generated!", state="complete", expanded=False)
            st.rerun()

if st.session_state.resume_text:
    # ── Initialize State ──
    if not st.session_state.get("edit_state_initialized"):
        from llm_utils import extract_resume_fields_via_llm
        from resume_builder import _extract_name, _extract_section
        
        with st.spinner("🔍 Parsing and structuring resume details using AI..."):
            extracted_fields = extract_resume_fields_via_llm(st.session_state.resume_text)
            
        if extracted_fields:
            st.session_state.edit_name = extracted_fields.get("name", "")
            st.session_state.edit_summary = extracted_fields.get("summary", "")
            st.session_state.edit_skills_languages = extracted_fields.get("skills_languages", "")
            st.session_state.edit_skills_tools = extracted_fields.get("skills_tools", "")
            st.session_state.edit_skills_soft = extracted_fields.get("skills_soft", "")
            st.session_state.edit_experience = extracted_fields.get("experience", "")
            st.session_state.edit_education = extracted_fields.get("education", "")
            st.session_state.edit_achievements = extracted_fields.get("achievements", "")
            st.session_state.edit_certs_projects = extracted_fields.get("certs_projects", "")
        else:
            # Fallback to naive heuristics
            st.session_state.edit_name = _extract_name(st.session_state.resume_text)
            summary_text = ""
            paragraphs = [p.strip() for p in st.session_state.resume_text.split("\n\n") if p.strip()]
            if paragraphs:
                summary_text = paragraphs[0] if len(paragraphs[0].split()) > 5 else (paragraphs[1] if len(paragraphs) > 1 else "")
            st.session_state.edit_summary = summary_text
            st.session_state.edit_skills_languages = ""
            st.session_state.edit_skills_tools = ", ".join(st.session_state.skills) if st.session_state.skills else _extract_section(st.session_state.resume_text, "Skills")
            st.session_state.edit_skills_soft = ""
            st.session_state.edit_experience = _extract_section(st.session_state.resume_text, "Experience")
            st.session_state.edit_education = _extract_section(st.session_state.resume_text, "Education")
            st.session_state.edit_achievements = _extract_section(st.session_state.resume_text, "Achievements")
            certs = _extract_section(st.session_state.resume_text, "Certifications")
            projects = _extract_section(st.session_state.resume_text, "Projects")
            st.session_state.edit_certs_projects = "\n".join(filter(None, [certs, projects]))
            
        # Clear the old structured list states so they get re-initialized on every new resume parsing
        for list_key in [
            "edit_experience_list", "edit_education_list", "edit_projects_list",
            "edit_achievements_list", "edit_skills_languages_list",
            "edit_skills_tools_list", "edit_skills_soft_list"
        ]:
            if list_key in st.session_state:
                del st.session_state[list_key]
            
        st.session_state.edit_state_initialized = True
        
    view_mode = st.radio("Candidate Hub Mode:", ["📊 VMock Report & Insights", "✍️ Interactive Resume Editor"], horizontal=True)
    
    if view_mode == "✍️ Interactive Resume Editor":
        render_resume_editor()
        st.stop()
        
    role = st.session_state.predicted_role or "Professional"
    ats = int((st.session_state.ats_ml_score or {"score": 0})["score"])
    
    # DB Save
    if not st.session_state.db_saved:
        try:
            email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", st.session_state.resume_text)
            email = email_match.group(0) if email_match else "unknown@email.com"
            name = st.session_state.resume_text.splitlines()[0][:30]
            health = st.session_state.health_data["score"]
            strong = sum(1 for b in st.session_state.bullet_results if b["label"] == "Strong")
            insert_candidate(name, email, "", role, ats, health, strong)
            
            # Save resume to user account if logged in
            if st.session_state.get('user_id'):
                os.makedirs("data/saved_resumes", exist_ok=True)
                saved_path = f"data/saved_resumes/{st.session_state.user_id}_{int(__import__('time').time())}.pdf"
                if st.session_state.resume_path and os.path.exists(st.session_state.resume_path):
                    shutil.copy2(st.session_state.resume_path, saved_path)
                
                # Compute ML Centroid Score
                centroid = get_domain_centroid_score(st.session_state.resume_text, role)
                save_user_resume(st.session_state.user_id, saved_path, False, health, role, centroid)
            
            st.session_state.db_saved = True
        except:
            pass
    
    # --- My Saved Resumes Gallery ---
    if st.session_state.get('user_id'):
        saved_resumes = get_user_resumes(st.session_state.user_id)
        if saved_resumes:
            with st.expander(f"📂 My Saved Resumes ({len(saved_resumes)}/4)", expanded=False):
                for i, res in enumerate(saved_resumes):
                    badge = "🌟 Enhanced" if res['is_enhanced'] else "📄 Original"
                    rcol1, rcol2, rcol3 = st.columns([3, 1, 1])
                    with rcol1:
                        st.markdown(f"**{badge}** — {res['domain']} — Uploaded: {res['upload_date'][:10]}")
                    with rcol2:
                        st.markdown(f"Health: **{res['health_score']}** | Centroid: **{res['centroid_score']}**")
                    with rcol3:
                        if os.path.exists(res['file_path']):
                            with open(res['file_path'], 'rb') as rf:
                                st.download_button("⬇️", rf.read(), file_name=f"resume_{i+1}.pdf", key=f"dl_saved_{i}")
                    st.markdown("---")

    st.markdown("---")
    
    # LinkedIn & Salary Card
    salary = estimate_salary(role, ats)
    st.markdown(f"""
    <div class='info-card'>
        <h1 style='color: #0369A1; font-size: 2.5rem; margin-bottom: 5px;'>Resume Health Score</h1>
        <p style='color: #0C4A6E; font-size: 1.1rem; margin-top: 0;'>A comprehensive analysis of your resume's impact and readability.</p>
        <h3 style='margin-top:0; color:#0369A1;'>Estimated Market Value: {salary}</h3>
    </div>
    """, unsafe_allow_html=True)

    @st.dialog("Your Auto-Generated LinkedIn Bio")
    def show_linkedin_bio():
        skills_str = ", ".join(st.session_state.skills[:5]) if st.session_state.skills else "problem-solving"
        bio = f"Driven and detail-oriented {role} with a proven track record of delivering high-quality results. Skilled in {skills_str}, I thrive in collaborative environments where I can leverage technology to solve complex problems.\n\nAlways eager to learn and adapt to new challenges, I am currently looking for opportunities to bring my expertise to an innovative team."
        st.write("Copy and paste this into your LinkedIn 'About' section:")
        st.code(bio, language="markdown")

    if st.button("🔵 Generate LinkedIn Bio"):
        show_linkedin_bio()

    st.markdown("---")
    yoe = st.session_state.get("yoe", 0.0)
    st.header(f"📊 VMock Benchmark Report: {role} ({yoe} YoE)")
    st.markdown("Your resume is scored on three academic pillars: Impact, Presentation, and Competencies.")
    
    # Calculate VMock Pillars
    # 1. Presentation = Formatting Health
    presentation_score = st.session_state.health_data["score"]
    
    # 2. Competencies = ATS Market Skill Alignment (from gaps)
    competencies_score = 100
    gaps = st.session_state.market_gaps or {"matched": [], "missing": []}
    if len(gaps["matched"]) + len(gaps["missing"]) > 0:
        competencies_score = int((len(gaps["matched"]) / (len(gaps["matched"]) + len(gaps["missing"]))) * 100)
        
    # 3. Impact = Ratio of Strong Bullets
    bullets = st.session_state.bullet_results
    strong_count = sum(1 for b in bullets if b["label"] == "Strong")
    impact_score = int((strong_count / max(1, len(bullets))) * 100)
    
    # Row 1: Scores
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("### Impact Score")
        fig_impact = create_gauge_chart(impact_score, "Bullet Point Strength")
        st.pyplot(fig_impact)
        plt.close(fig_impact)
        
    with c2:
        st.markdown("### Presentation Score")
        fig_health = create_gauge_chart(presentation_score, "Formatting Health")
        st.pyplot(fig_health)
        plt.close(fig_health)
        
    with c3:
        st.markdown("### Competencies Score")
        fig_comp = create_gauge_chart(competencies_score, "Hard Skill Alignment")
        st.pyplot(fig_comp)
        plt.close(fig_comp)
        
    st.markdown("### 🧠 Explainable AI (XAI) Insights")
    xai_bullets = []
    if impact_score > 80:
        xai_bullets.append("✅ **High Impact:** Your Random Forest score was significantly boosted by a strong presence of Action Verbs and Metrics in your bullet points.")
    else:
        xai_bullets.append("⚠️ **Low Impact Penalty:** Your score was penalized due to a lack of quantifiable metrics. Adding numbers to your achievements will increase your score.")
        
    if presentation_score > 85:
        xai_bullets.append("✅ **Clean Presentation:** The parser easily extracted your data due to excellent formatting health.")
    else:
        xai_bullets.append("⚠️ **Formatting Penalty:** The ML engine struggled to parse some sections. Fix your margins or font consistency to prevent ATS rejection.")
        
    if competencies_score > 75:
        xai_bullets.append("✅ **Market Aligned:** You possess a high density of the hard skills expected for this specific role, boosting your Competencies score.")
    else:
        xai_bullets.append("⚠️ **Skill Gap Penalty:** Your resume lacks critical skills required for the current market, heavily weighing down your Resume Health Score.")

    for insight in xai_bullets:
        st.markdown(insight)

    st.markdown("---")
    
    # Row 2: Skills & Gaps
    col_gaps, col_radar = st.columns([1.5, 1])
    
    with col_radar:
        st.markdown("### 🕸️ Skill Distribution")
        skill_cats = categorize_skills(st.session_state.skills or [])
        fig_radar = create_radar_chart(skill_cats)
        st.pyplot(fig_radar)
        plt.close(fig_radar)
        
        st.markdown("### ☁️ Keyword Cloud")
        fig_cloud = create_word_cloud(st.session_state.resume_text)
        st.pyplot(fig_cloud)
        plt.close(fig_cloud)

    with col_gaps:
        st.markdown("### 📈 Market Gap & Skills Improvement")
        gaps = st.session_state.market_gaps
        if gaps["missing"]:
            st.error("⚠️ **Missing In-Demand Skills:** Add these to boost your Resume Health Score for this role.")
            missing_html = "".join([f"<span class='skill-tag skill-miss'>{s}</span>" for s in gaps["missing"]])
            st.markdown(missing_html, unsafe_allow_html=True)
        else:
            st.success("✅ No major market gaps detected for this role!")
            
        st.markdown("✅ **Your Top Skills:**")
        matched_html = "".join([f"<span class='skill-tag skill-match'>{s}</span>" for s in gaps["matched"][:10]])
        st.markdown(matched_html, unsafe_allow_html=True)
        
        st.markdown("### 🛠️ Formatting Issues to Fix")
        if not st.session_state.issues:
            st.success("No formatting issues found!")
        else:
            for issue in st.session_state.issues:
                st.warning(f"**{issue['severity'].upper()}**: {issue['issue']}")

    st.markdown("---")
    
    # Live Upskilling Recommender
    st.header("🎓 Automated Upskilling Recommender")
    st.markdown("Bridge your market gap. We've scraped the web for the top real-life courses for your missing skills.")
    
    if gaps["missing"]:
        from course_scraper import fetch_courses
        
        top_3_missing = gaps["missing"][:3]
        
        # Create 'Slide View' using tabs
        tabs = st.tabs(top_3_missing)
        
        for i, skill in enumerate(top_3_missing):
            with tabs[i]:
                st.markdown(f"**Top recommendations for:** `{skill}`")
                
                with st.spinner(f"📡 Live scraping YouTube & Aggregators for '{skill}' courses..."):
                    courses = fetch_courses(skill, limit=3)
                    
                if not courses:
                    st.info(f"Could not fetch live courses for {skill}. Try checking Udemy manually.")
                else:
                    cols = st.columns(3)
                    for j, course in enumerate(courses[:3]):
                        with cols[j]:
                            st.markdown(f"""
                            <div style='background:#FFFFFF; padding:15px; border-radius:8px; border:1px solid #E2E8F0; box-shadow:0 2px 4px rgba(0,0,0,0.05); height:100%;'>
                                <span style='font-size:12px; color:#64748B; font-weight:bold;'>{course['platform'].upper()}</span>
                                <h5 style='color:#1E293B; margin:8px 0;'>{course['title'][:60]}{"..." if len(course['title'])>60 else ""}</h5>
                                <a href="{course['url']}" target="_blank" style='text-decoration:none; color:#2563EB; font-weight:bold; font-size:14px;'>Watch Course ↗</a>
                            </div>
                            """, unsafe_allow_html=True)
    else:
        st.success("You are fully aligned with the required market skills! No urgent upskilling required.")

    st.markdown("---")
    
    # Row 3: ResumeWorded Line-by-Line Breakdown
    st.markdown("### ✍️ Line-by-Line Bullet Breakdown")
    st.markdown("We've extracted every bullet point on your resume. Here is granular, line-by-line feedback on your writing.")
    
    for b in bullets:
        text = b['text']
        # ResumeWorded Logic checks for Action Verbs and Numbers
        action_verbs = ["developed", "led", "managed", "created", "built", "improved", "designed", "optimized", "spearheaded", "implemented"]
        has_action = any(v in text.lower() for v in action_verbs)
        has_metric = bool(re.search(r'\b\d+%\b|\$\d+|\b\d+\b', text))
        
        feedback = []
        # Check for action verb
        if not has_action:
            feedback.append("Missing strong action verb (e.g. 'led', 'developed').")
            
        # Only require a metric if the bullet describes an impact/achievement/scale
        impact_words = ["increase", "decrease", "improve", "reduce", "grow", "save", "cut", "boost",
                        "revenue", "scale", "user", "load", "latency", "time", "speed", "performance",
                        "cost", "budget", "efficient", "optimize", "accelerate", "expand", "lead", "manage"]
        needs_metric = any(w in text.lower() for w in impact_words)
        
        if needs_metric and not has_metric:
            feedback.append("Missing quantifiable metric (e.g. '20%', '$50k', '5+ developers').")
            
        if not feedback:
            st.markdown(f"<div class='bullet-card b-strong'>✅ <strong>Perfect Impact</strong><br><i>\"{text}\"</i></div>", unsafe_allow_html=True)
        else:
            feedback_str = " | ".join(feedback)
            st.markdown(f"<div class='bullet-card b-weak'>⚠️ <strong>Needs Work</strong><br><i>\"{text}\"</i><br><span class='b-sugg'>💡 Feedback: {feedback_str}</span></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.header("🤖 Smart Resume Enhancer")
    st.markdown("We've generated targeted questions based on the gaps above. Answer them to instantly download an enhanced PDF.")
    
    if not st.session_state.interview_qs:
        st.session_state.interview_qs = generate_interview_questions(
            st.session_state.issues or [], 
            st.session_state.skills or [], 
            st.session_state.market_gaps or {"matched": [], "missing": []}, 
            st.session_state.bullet_results or []
        )
    
    answers = {}
    for i, q in enumerate(st.session_state.interview_qs):
        answers[q] = st.text_area(f"Q{i+1}: {q}", key=f"q_{i}")
    
    st.markdown("### 🎨 Customize PDF Styling & Template")
    with st.expander("PDF Formatting Options", expanded=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            pdf_template = st.selectbox("Template Style", ["Classic Modern", "Minimalist", "Executive"], index=0)
            pdf_font = st.selectbox("Font Family", ["Helvetica", "Times", "Courier"], index=0)
            pdf_color = st.selectbox("Color Theme", ["Dark Blue", "Black", "Green", "Crimson Red", "Slate Grey"], index=0)
        with col_f2:
            pdf_page_size = st.selectbox("Page Size", ["A4", "Letter"], index=0)
            pdf_font_size = st.slider("Base Font Size (pt)", min_value=8, max_value=14, value=10, step=1)
            pdf_margin = st.slider("Page Margin (mm)", min_value=10, max_value=30, value=15, step=5)
            
    if st.button("🚀 Generate Enhanced Resume PDF", type="primary"):
        filled = [a for a in answers.values() if a.strip()]
        if not filled:
            st.warning("Please answer at least one question.")
        else:
            with st.spinner("Compiling PDF..."):
                output_path = os.path.join(tempfile.gettempdir(), "enhanced_resume.pdf")
                generate_enhanced_pdf(
                    st.session_state.resume_text, answers, st.session_state.skills or [],
                    role, output_path,
                    font_family=pdf_font,
                    base_font_size=pdf_font_size,
                    margin=pdf_margin,
                    primary_color_name=pdf_color,
                    page_size=pdf_page_size,
                    template_style=pdf_template
                )
            st.balloons()
            st.success("✅ Enhanced resume generated!")
            
            # Save enhanced resume to user account
            if st.session_state.get('user_id'):
                os.makedirs("data/saved_resumes", exist_ok=True)
                enh_path = f"data/saved_resumes/{st.session_state.user_id}_enhanced_{int(__import__('time').time())}.pdf"
                shutil.copy2(output_path, enh_path)
                health = st.session_state.health_data["score"] if st.session_state.health_data else 0
                centroid = get_domain_centroid_score(st.session_state.resume_text, role)
                save_user_resume(st.session_state.user_id, enh_path, True, health, role, centroid)
                st.toast("Enhanced resume saved to your account!")
            
            with open(output_path, "rb") as f:
                st.download_button("📥 Download PDF", data=f, file_name="enhanced_resume.pdf", mime="application/pdf")
