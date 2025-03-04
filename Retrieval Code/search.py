# search_engine.py
from db import SupabaseConnector
from llm_process import QueryProcessor
from config import RELEVANCE_THRESHOLD, MAX_RESULTS

class ClipSearchEngine:
    def __init__(self):
        """Initialize search engine components"""
        self.db = SupabaseConnector()
        self.processor = QueryProcessor()
        self.threshold = RELEVANCE_THRESHOLD
        self.max_results = MAX_RESULTS
    
    def search(self, user_query):
        """Execute search for clips matching the user query"""
        print(f"Processing search: '{user_query}'")
        
        # Extract structured search terms from query
        search_terms = self.processor.extract_search_terms(user_query)
        print(f"Extracted terms: {search_terms}")
        
        # Get potential matches using keyword filtering
        potential_matches = self._get_potential_matches(search_terms)
        print(f"Found {len(potential_matches)} potential matches")
        
        # If no matches from keyword search, try with all clips
        if not potential_matches:
            print("No keyword matches, trying with all clips")
            potential_matches = self.db.get_all_clips()
        
        # Limit to reasonable number before semantic ranking
        if len(potential_matches) > 50:
            potential_matches = potential_matches[:50]
        
        # Rank results by semantic relevance
        ranked_results = self.processor.rank_clips(
            user_query, 
            potential_matches,
            self.threshold
        )
        
        # Limit number of results
        results = ranked_results[:self.max_results] if len(ranked_results) > self.max_results else ranked_results
        
        return results
    
    def _get_potential_matches(self, search_terms):
        """Get potential matches using keyword filtering"""
        all_terms = []
        
        # Extract all keywords from search terms
        for category in search_terms.values():
            if isinstance(category, list):
                all_terms.extend(category)
            elif isinstance(category, str):
                all_terms.append(category)
        
        # Filter out terms that are too short
        keywords = [term for term in all_terms if term and len(term) > 2]
        
        # If no valid keywords, return empty list
        if not keywords:
            return []
        
        # Try each keyword and collect results
        all_matches = []
        seen_ids = set()
        
        for keyword in keywords:
            matches = self.db.get_clips_by_keyword(keyword)
            for match in matches:
                if match["id"] not in seen_ids:
                    all_matches.append(match)
                    seen_ids.add(match["id"])
        
        return all_matches