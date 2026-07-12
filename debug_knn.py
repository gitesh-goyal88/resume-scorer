import sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from text_utils import preprocess, identity_tokenizer
from job_matcher import load_jobs_corpus

def debug_knn():
    jobs = load_jobs_corpus()
    if not jobs:
        print("No jobs")
        return

    job_texts = [job["description"] for job in jobs]
    processed_job_texts = [preprocess(text) for text in job_texts]
    
    count_vectorizer = CountVectorizer(tokenizer=identity_tokenizer, preprocessor=identity_tokenizer, token_pattern=None)
    job_count_vectors = count_vectorizer.fit_transform(processed_job_texts)
    knn = NearestNeighbors(n_neighbors=5, metric='cosine')
    knn.fit(job_count_vectors)
    
    domains = ["Data Science", "Python Backend", "Frontend React", "DevOps Engineer", "Machine Learning", "HR Manager"]
    
    for domain in domains:
        print(f"\\n--- Query: {domain} ---")
        query_processed = preprocess(domain)
        print("Processed Query:", query_processed)
        
        knn_query_vector = count_vectorizer.transform([query_processed])
        print("Vector non-zero elements:", knn_query_vector.nnz)
        
        if knn_query_vector.nnz > 0:
            distances, indices = knn.kneighbors(knn_query_vector)
            top5_knn = indices[0]
            print("Distances:", distances[0])
            print("Indices:", top5_knn)
            
            domain_keywords = domain.lower().split()
            hits = 0
            for idx in top5_knn:
                title = str(jobs[idx].get("title", "")).lower()
                relevant = any(k in title for k in domain_keywords)
                if relevant: hits += 1
                print(f"[{relevant}] Title: {title}")
            print(f"Precision@5: {hits/5.0}")
        else:
            print("Vector is entirely zero!")

if __name__ == "__main__":
    debug_knn()
