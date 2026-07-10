import streamlit as st
import pandas as pd
import numpy as np
import time
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from text_utils import preprocess, identity_tokenizer
from job_matcher import load_jobs_corpus
from ui_utils import inject_custom_css

inject_custom_css()

st.markdown("<h1 class='gradient-title' style='font-size: 3rem; margin-bottom: 5px; padding-bottom: 5px;'>📈 ML Analytics</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-heading'>Dynamic quantitative analysis of TF-IDF and BM25 ranking performance for your specific resume.</p>", unsafe_allow_html=True)

if "resume_text" not in st.session_state or not st.session_state.resume_text:
    st.markdown('''
    <div style='background: #18181B; border: 1px dashed rgba(255,255,255,0.15); border-radius: 18px; padding: 40px; text-align: center; margin-top: 20px;'>
        <h3 style='color: #FAFAFA; margin-bottom: 8px;'>No Resume Data</h3>
        <p style='color: #A1A1AA; font-family: Inter; margin-bottom: 24px;'>Please upload a resume on the Dashboard to run the dynamic ML evaluation.</p>
        <a href='/' target='_self' style='text-decoration: none;'><button style='background-color: #22C55E; color: #000000; border: none; border-radius: 99px; font-weight: 700; padding: 10px 24px; cursor: pointer;'>Go to Dashboard</button></a>
    </div>
    ''', unsafe_allow_html=True)
    st.stop()

resume_text = st.session_state.resume_text
predicted_role = st.session_state.get("predicted_role", "")
user_name = st.session_state.get("user_name") or st.session_state.get("edit_name") or "User"
first_name = user_name.split()[0]

if not predicted_role:
    st.error("Error: Predicted role not found. Please regenerate your report on the Dashboard.")
    st.stop()

st.markdown(f"### Evaluating Match Accuracy for: `{predicted_role}`")
st.markdown(f"We are dynamically running your resume through both algorithms. A job is considered a 'True Positive' (relevant) if its title matches your AI-predicted role.")

with st.spinner("Running Information Retrieval algorithms..."):
    jobs = load_jobs_corpus()
    if not jobs:
        st.error("Job corpus is empty.")
        st.stop()

    job_texts = [job["description"] for job in jobs]
    corpus = job_texts + [resume_text]
    processed_corpus = [preprocess(text) for text in corpus]

    resume_tokens = processed_corpus[-1]
    job_tokens = processed_corpus[:-1]

    # --- TF-IDF ---
    start_time = time.time()
    vectorizer = TfidfVectorizer(tokenizer=identity_tokenizer, preprocessor=identity_tokenizer, token_pattern=None)
    tfidf_matrix = vectorizer.fit_transform(processed_corpus)
    resume_vector = tfidf_matrix[-1]
    job_vectors = tfidf_matrix[:-1]
    tfidf_sim = cosine_similarity(resume_vector, job_vectors).flatten()
    tfidf_top_5 = np.argsort(tfidf_sim)[::-1][:5]
    tfidf_time = time.time() - start_time

    # --- BM25 ---
    start_time = time.time()
    bm25 = BM25Okapi(job_tokens)
    bm25_scores = bm25.get_scores(resume_tokens)
    bm25_top_5 = np.argsort(bm25_scores)[::-1][:5]
    bm25_time = time.time() - start_time

    # Evaluate Precision@5
    role_keywords = predicted_role.lower().split()
    
    def is_relevant(job_idx):
        title = str(jobs[job_idx].get("title", "")).lower()
        return any(k in title for k in role_keywords)

    tfidf_hits = sum([1 for idx in tfidf_top_5 if is_relevant(idx)])
    bm25_hits = sum([1 for idx in bm25_top_5 if is_relevant(idx)])

    tfidf_p5 = tfidf_hits / 5.0
    bm25_p5 = bm25_hits / 5.0

st.markdown("### 🏆 Live Metrics Comparison: TF-IDF vs BM25")

metrics_data = {
    "Metric": ["Precision@5 (Relevance in Top 5)", "Execution Time (Seconds)", "Top Score Confidence"],
    "TF-IDF": [f"{tfidf_p5:.2f}", f"{tfidf_time:.4f}s", f"{tfidf_sim[tfidf_top_5[0]]:.2f}"],
    "BM25": [f"{bm25_p5:.2f}", f"{bm25_time:.4f}s", f"{bm25_scores[bm25_top_5[0]]:.2f}"]
}

df_metrics = pd.DataFrame(metrics_data)

# Custom styler for dark mode highlighting
def highlight_better(row):
    styles = [''] * len(row)
    if row.name == 0:  # Precision
        if float(row['TF-IDF']) > float(row['BM25']): styles[1] = 'background-color: #064E3B; color: #FAFAFA'
        elif float(row['BM25']) > float(row['TF-IDF']): styles[2] = 'background-color: #064E3B; color: #FAFAFA'
    elif row.name == 1:  # Time (Lower is better)
        t_tfidf = float(row['TF-IDF'].replace('s', ''))
        t_bm25 = float(row['BM25'].replace('s', ''))
        if t_tfidf < t_bm25: styles[1] = 'background-color: #064E3B; color: #FAFAFA'
        elif t_bm25 < t_tfidf: styles[2] = 'background-color: #064E3B; color: #FAFAFA'
    return styles

st.dataframe(df_metrics.style.apply(highlight_better, axis=1), use_container_width=True)

st.markdown("### Academic Conclusion")
st.success(f"""
**Dynamic Analysis for {first_name if 'first_name' in locals() else 'User'}:**
Based on your specific resume, **{'BM25' if bm25_p5 >= tfidf_p5 else 'TF-IDF'}** performed better at retrieving relevant {predicted_role} jobs in its top 5 results. 

BM25 often achieves superior results by mathematically penalizing overly long job descriptions (length normalization) and preventing keyword stuffing (term frequency saturation).
""")
