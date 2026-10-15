"""
RAG Engine for Freight Tiger Shipping Cost Assistant
Implements vector/text retrieval over context notes using TF-IDF semantic matching
combined with corridor and temporal metadata filtering.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ContextNotesRAG:
    """
    RAG retriever for context notes with hybrid semantic and metadata ranking.
    """
    def __init__(self, notes_file_path: str):
        self.notes_file_path = notes_file_path
        self.notes_df = pd.read_csv(notes_file_path)
        self.notes_df['date'] = pd.to_datetime(self.notes_df['date'])
        
        # Build text corpus for vector indexing
        # Combine corridor + date + note text
        self.corpus = []
        for _, row in self.notes_df.iterrows():
            text_rep = (
                f"Note ID: {row['note_id']}. "
                f"Corridor: {row['applies_to']}. "
                f"Date: {row['date'].strftime('%Y-%m-%d')}. "
                f"Event details: {row['note']}"
            )
            self.corpus.append(text_rep)
            
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

    def retrieve_candidates(
        self,
        route: str,
        week_of: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieves candidate notes for a given route and week.
        Scores candidates based on corridor match, temporal proximity, and semantic similarity.
        """
        query_date = pd.to_datetime(week_of)
        
        query_text = f"Freight route {route} week of {week_of} shipping cost rate change delay surcharge diesel road weather"
        query_vec = self.vectorizer.transform([query_text])
        text_sims = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        
        scored_candidates = []
        
        for idx, row in self.notes_df.iterrows():
            note_date = row['date']
            applies_to = str(row['applies_to']).strip()
            note_id = str(row['note_id']).strip()
            note_text = str(row['note']).strip()
            
            # Temporal distance in days
            days_diff = abs((query_date - note_date).days)
            
            # Corridor alignment
            is_direct_route_match = (applies_to == route)
            is_all_routes = (applies_to.lower() == 'all routes')
            
            if is_direct_route_match:
                corridor_score = 1.0
            elif is_all_routes:
                corridor_score = 0.5
            else:
                corridor_score = 0.0
                
            # Temporal decay score (halves every 14 days, capped at 120 days)
            temporal_score = max(0.0, 1.0 - (days_diff / 90.0))
            
            # Semantic text score from vectorizer
            semantic_score = float(text_sims[idx])
            
            # Total composite retrieval score
            composite_score = (
                corridor_score * 0.45 +
                temporal_score * 0.35 +
                semantic_score * 0.20
            )
            
            scored_candidates.append({
                'note_id': note_id,
                'date': note_date.strftime('%Y-%m-%d'),
                'applies_to': applies_to,
                'note': note_text,
                'days_diff': days_diff,
                'is_direct_route_match': is_direct_route_match,
                'is_all_routes': is_all_routes,
                'corridor_score': corridor_score,
                'temporal_score': temporal_score,
                'semantic_score': semantic_score,
                'composite_score': composite_score
            })
            
        # Sort descending by composite score, then by temporal proximity
        scored_candidates.sort(key=lambda x: (x['composite_score'], -x['days_diff']), reverse=True)
        return scored_candidates[:top_k]
