import streamlit as st
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from text_utils import preprocess, identity_tokenizer
from job_matcher import load_jobs_corpus
from ui_utils import inject_custom_css

inject_custom_css()

st.markdown("<h1 class='gradient-title' style='font-size: 3rem; margin-bottom: 5px; padding-bottom: 5px;'>📈 ML Analytics</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-heading'>Comprehensive evaluation of Search Algorithms (TF-IDF vs BM25 vs KNN) across professional domains.</p>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🌎 Global Benchmarks", "👤 Personal Resume Match"])

# ----------------- GLOBALS -----------------
with st.spinner("Initializing models..."):
    jobs = load_jobs_corpus()
    if not jobs:
        st.error("Job corpus is empty.")
        st.stop()

    job_texts = [job["description"] for job in jobs]
    processed_job_texts = [preprocess(text) for text in job_texts]
    
    # Pre-compute TF-IDF
    vectorizer = TfidfVectorizer(tokenizer=identity_tokenizer, preprocessor=identity_tokenizer, token_pattern=None)
    job_vectors = vectorizer.fit_transform(processed_job_texts)
    
    # Pre-compute KNN
    knn = NearestNeighbors(n_neighbors=5, metric='cosine')
    knn.fit(job_vectors)

    # Pre-compute BM25
    bm25 = BM25Okapi(processed_job_texts)


# ==========================================
# TAB 1: GLOBAL BENCHMARKS
# ==========================================
with tab1:
    st.markdown("### 📊 Global Search Performance")
    st.markdown("We evaluate the Precision@5 of each algorithm by simulating search queries for different professional fields.")
    
    domains = ["Data Science", "Python Backend", "Frontend React", "DevOps Engineer", "Machine Learning", "HR Manager"]
    algorithms = ["TF-IDF", "BM25", "KNN"]
    
    @st.cache_data(show_spinner=False)
    def compute_global_metrics():
        p_matrix = np.zeros((len(domains), len(algorithms)))
        times = [0.0, 0.0, 0.0]
        
        for i, domain in enumerate(domains):
            query_processed = preprocess(domain)
            query_vector = vectorizer.transform([query_processed])
            
            # Ground truth evaluator
            domain_keywords = domain.lower().split()
            def is_relevant(job_idx):
                title = str(jobs[job_idx].get("title", "")).lower()
                return any(k in title for k in domain_keywords)
            
            # --- TF-IDF ---
            t0 = time.time()
            sim = cosine_similarity(query_vector, job_vectors).flatten()
            top5_tfidf = np.argsort(sim)[::-1][:5]
            times[0] += (time.time() - t0)
            p_matrix[i, 0] = sum(1 for idx in top5_tfidf if is_relevant(idx)) / 5.0
            
            # --- BM25 ---
            t0 = time.time()
            scores = bm25.get_scores(query_processed)
            top5_bm25 = np.argsort(scores)[::-1][:5]
            times[1] += (time.time() - t0)
            p_matrix[i, 1] = sum(1 for idx in top5_bm25 if is_relevant(idx)) / 5.0
            
            # --- KNN ---
            t0 = time.time()
            distances, indices = knn.kneighbors(query_vector)
            top5_knn = indices[0]
            times[2] += (time.time() - t0)
            p_matrix[i, 2] = sum(1 for idx in top5_knn if is_relevant(idx)) / 5.0
            
        return p_matrix, [t/len(domains) for t in times]

    with st.spinner("Computing precision matrix (Running 18 searches)..."):
        precision_matrix, exec_times = compute_global_metrics()
        
    avg_precision = np.mean(precision_matrix, axis=0)
    
    win_rates = [0, 0, 0]
    for i in range(len(domains)):
        winner_idx = np.argmax(precision_matrix[i])
        win_rates[winner_idx] += 1

    # Apply global dark theme for Matplotlib
    plt.style.use('dark_background')
    plt.rcParams.update({
        'figure.facecolor': '#18181B',
        'axes.facecolor': '#18181B',
        'axes.edgecolor': '#3B3B40',
        'text.color': '#FAFAFA',
        'axes.labelcolor': '#FAFAFA',
        'xtick.color': '#A1A1AA',
        'ytick.color': '#A1A1AA',
        'font.family': 'sans-serif'
    })
    colors = ['#3B82F6', '#10B981', '#F59E0B']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Precision Heatmap (P@5)")
        fig1, ax1 = plt.subplots(figsize=(7, 5))
        cax = ax1.imshow(precision_matrix, cmap='Greens', vmin=0, vmax=1.0)
        ax1.set_xticks(np.arange(len(algorithms)))
        ax1.set_yticks(np.arange(len(domains)))
        ax1.set_xticklabels(algorithms)
        ax1.set_yticklabels(domains)
        
        for i in range(len(domains)):
            for j in range(len(algorithms)):
                val = precision_matrix[i, j]
                text_color = 'black' if val > 0.5 else 'white'
                ax1.text(j, i, f"{val:.2f}", ha="center", va="center", color=text_color, fontweight='bold')
        
        fig1.colorbar(cax, ax=ax1, fraction=0.046, pad=0.04)
        st.pyplot(fig1)
        
    with col2:
        st.markdown("#### Average Precision@5")
        fig2, ax2 = plt.subplots(figsize=(7, 5))
        bars = ax2.bar(algorithms, avg_precision, color=colors, alpha=0.9)
        ax2.set_ylim(0, 1.0)
        ax2.grid(axis='y', color='#2A2A2E', linestyle='--', alpha=0.7)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        for bar in bars:
            yval = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2, yval + 0.02, f"{yval:.2f}", ha='center', va='bottom', color='#FAFAFA', fontweight='bold')
        st.pyplot(fig2)

    st.markdown("---")
    
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### Algorithm Win Rate")
        fig3, ax3 = plt.subplots(figsize=(6, 5))
        if sum(win_rates) > 0:
            ax3.pie(win_rates, labels=algorithms, colors=colors, autopct='%1.1f%%', startangle=90, 
                    textprops={'color': '#FAFAFA', 'fontweight': 'bold'},
                    wedgeprops={'edgecolor': '#18181B', 'linewidth': 2})
            st.pyplot(fig3)
        else:
            st.warning("Not enough data to calculate win rates.")
            
    with col4:
        st.markdown("#### Tradeoff: Speed vs Accuracy")
        fig4, ax4 = plt.subplots(figsize=(7, 5))
        for i, algo in enumerate(algorithms):
            ax4.scatter(exec_times[i], avg_precision[i], color=colors[i], s=200, label=algo, alpha=0.9, edgecolors='#FAFAFA', linewidth=1.5)
            ax4.annotate(algo, (exec_times[i], avg_precision[i]), xytext=(10, -5), textcoords='offset points', color='#FAFAFA', fontweight='bold')
            
        ax4.set_xlabel("Avg Execution Time (Seconds)")
        ax4.set_ylabel("Average Precision@5")
        ax4.grid(color='#2A2A2E', linestyle='--', alpha=0.7)
        ax4.spines['top'].set_visible(False)
        ax4.spines['right'].set_visible(False)
        st.pyplot(fig4)


# ==========================================
# TAB 2: PERSONAL RESUME MATCH
# ==========================================
with tab2:
    if "resume_text" not in st.session_state or not st.session_state.resume_text:
        st.info("Please upload a resume on the Dashboard to see your personal evaluation.")
        st.stop()
        
    resume_text = st.session_state.resume_text
    predicted_role = st.session_state.get("predicted_role", "")
    user_name = st.session_state.get("user_name") or st.session_state.get("edit_name") or "User"
    first_name = user_name.split()[0]
    
    if not predicted_role:
        st.error("Predicted role not found. Please regenerate your report on the Dashboard.")
        st.stop()
        
    st.markdown(f"### Evaluating Match Accuracy for: `{predicted_role}`")
    st.markdown("A job is considered a 'True Positive' (relevant) if its title matches your AI-predicted role.")
    
    with st.spinner("Running your resume through algorithms..."):
        resume_processed = preprocess(resume_text)
        resume_vector = vectorizer.transform([resume_processed])
        
        role_keywords = predicted_role.lower().split()
        def is_relevant_personal(job_idx):
            title = str(jobs[job_idx].get("title", "")).lower()
            return any(k in title for k in role_keywords)

        # TF-IDF
        t0 = time.time()
        tfidf_sim = cosine_similarity(resume_vector, job_vectors).flatten()
        tfidf_top = np.argsort(tfidf_sim)[::-1][:5]
        t_tfidf = time.time() - t0
        p_tfidf = sum(1 for idx in tfidf_top if is_relevant_personal(idx)) / 5.0
        
        # BM25
        t0 = time.time()
        bm25_scores = bm25.get_scores(resume_processed)
        bm25_top = np.argsort(bm25_scores)[::-1][:5]
        t_bm25 = time.time() - t0
        p_bm25 = sum(1 for idx in bm25_top if is_relevant_personal(idx)) / 5.0
        
        # KNN
        t0 = time.time()
        distances, indices = knn.kneighbors(resume_vector)
        knn_top = indices[0]
        t_knn = time.time() - t0
        p_knn = sum(1 for idx in knn_top if is_relevant_personal(idx)) / 5.0

    st.markdown("### 🏆 Live Metrics Comparison")
    
    metrics_data = {
        "Metric": ["Precision@5", "Execution Time (s)", "Top Score Confidence"],
        "TF-IDF": [f"{p_tfidf:.2f}", f"{t_tfidf:.4f}", f"{tfidf_sim[tfidf_top[0]]:.2f}"],
        "BM25": [f"{p_bm25:.2f}", f"{t_bm25:.4f}", f"{bm25_scores[bm25_top[0]]:.2f}"],
        "KNN": [f"{p_knn:.2f}", f"{t_knn:.4f}", f"{1 - distances[0][0]:.2f}"]
    }
    
    df_metrics = pd.DataFrame(metrics_data)
    
    def highlight_max(row):
        styles = [''] * len(row)
        if row.name == 0:  # Precision
            vals = [float(row['TF-IDF']), float(row['BM25']), float(row['KNN'])]
            max_idx = np.argmax(vals) + 1
            styles[max_idx] = 'background-color: #064E3B; color: #FAFAFA'
        elif row.name == 1:  # Time
            vals = [float(row['TF-IDF']), float(row['BM25']), float(row['KNN'])]
            min_idx = np.argmin(vals) + 1
            styles[min_idx] = 'background-color: #064E3B; color: #FAFAFA'
        return styles
        
    st.dataframe(df_metrics.style.apply(highlight_max, axis=1), use_container_width=True)
    
    st.success(f"""
    **Dynamic Analysis for {first_name}:**
    Based on your specific resume, the top performing algorithms were compared. 
    BM25 typically achieves superior results through length normalization, while KNN clusters semantically similar vector spaces!
    """)
