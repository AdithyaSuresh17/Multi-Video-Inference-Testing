# search_engine.py
from db import SupabaseConnector
from llm_process import QueryProcessor
from config import RELEVANCE_THRESHOLD, MAX_RESULTS
from datetime import datetime, timedelta

class ClipSearchEngine:
    def __init__(self):
        """Initialize search engine components"""
        self.db = SupabaseConnector()
        self.processor = QueryProcessor()
        self.threshold = RELEVANCE_THRESHOLD
        self.max_results = MAX_RESULTS
    
    def search(self, user_query):
        """Execute search for clips matching the user query including temporal aspects"""
        print(f"Processing search: '{user_query}'")
        
        # Extract structured search terms from query
        search_terms = self.processor.extract_search_terms(user_query)
        print(f"Extracted terms: {search_terms}")
        
        # Parse time references if present
        time_constraints = None
        if "time_references" in search_terms and any(search_terms.get("time_references", {}).values()):
            time_constraints = self.processor.parse_time_references(search_terms["time_references"])
            print(f"Time constraints: {time_constraints}")
            
            # Fix the date format - convert ISO format to database text format
            if time_constraints.get("start_time"):
                time_constraints["start_time"] = time_constraints["start_time"].replace('T', ' ')
            if time_constraints.get("end_time"):
                time_constraints["end_time"] = time_constraints["end_time"].replace('T', ' ')
            print(f"Adjusted time constraints for DB format: {time_constraints}")
        
        # Special handling for full-day searches
        if time_constraints and time_constraints.get("start_time") and time_constraints.get("end_time"):
            # Check if this is a full day search (00:00:00 to 23:59:59)
            start_parts = time_constraints["start_time"].split(' ')
            end_parts = time_constraints["end_time"].split(' ')
            
            if len(start_parts) == 2 and len(end_parts) == 2:
                date_part_start = start_parts[0]
                date_part_end = end_parts[0]
                time_part_start = start_parts[1]
                time_part_end = end_parts[1]
                
                if (date_part_start == date_part_end and 
                    time_part_start == "00:00:00" and 
                    time_part_end == "23:59:59"):
                    
                    print(f"Using date pattern search for {date_part_start}")
                    potential_matches = self.db.get_clips_by_date(date_part_start)
                    
                    # Skip to ranking if we have matches
                    # Skip ranking for date-based searches - directly return results
                    if potential_matches:
                        print(f"Bypassing ranking for date-specific search, returning {len(potential_matches)} results directly")
                        # Format results with default high relevance score
                        for match in potential_matches:
                            match["relevance_score"] = 0.95  # Set a high default relevance
                        
                        # Limit number of results
                        results = potential_matches[:self.max_results]
                        return results
        
        # Standard search flow if not a full day search or if full day search found no results
        potential_matches = self._get_potential_matches(search_terms, time_constraints)
        print(f"Found {len(potential_matches)} potential matches")
        
        # If no matches, try with all clips within time constraints if specified
        if not potential_matches and time_constraints and (time_constraints.get("start_time") or time_constraints.get("end_time")):
            print("No keyword matches, trying with time constraints only")
            if time_constraints.get("start_time") and time_constraints.get("end_time"):
                potential_matches = self.db.get_clips_by_timeframe(
                    time_constraints["start_time"],
                    time_constraints["end_time"]
                )
            elif time_constraints.get("start_time"):
                # Only start time specified, use until now
                now_formatted = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                potential_matches = self.db.get_clips_by_timeframe(
                    time_constraints["start_time"],
                    now_formatted
                )
            elif time_constraints.get("end_time"):
                # Only end time specified, use from beginning of available data
                potential_matches = self.db.get_clips_by_timeframe(
                    "1970-01-01 00:00:00",  # Unix epoch start as earliest possible date
                    time_constraints["end_time"]
                )
        
        # If still no matches, try with all clips
        if not potential_matches:
            print("No matches with constraints, trying with all clips")
            potential_matches = self.db.get_all_clips()
        
        # Limit to reasonable number before semantic ranking
        if len(potential_matches) > 50:
            potential_matches = potential_matches[:50]
        
        # Include time relevance info in query if time constraints exist
        enhanced_query = user_query
        if time_constraints:
            time_info = ""
            if time_constraints.get("start_time"):
                time_info += f" from {time_constraints['start_time']}"
            if time_constraints.get("end_time"):
                time_info += f" until {time_constraints['end_time']}"
            if time_info:
                enhanced_query += f". Consider time relevance:{time_info}"
        
        # Rank results by semantic relevance
        ranked_results = self.processor.rank_clips(
            enhanced_query, 
            potential_matches,
            self.threshold
        )
        
        # Limit number of results
        results = ranked_results[:self.max_results] if len(ranked_results) > self.max_results else ranked_results
        
        return results
    
    def _get_potential_matches(self, search_terms, time_constraints=None):
        """Get potential matches using keyword filtering and time constraints"""
        all_terms = []
        
        # Extract all keywords from search terms
        for category in search_terms.values():
            if isinstance(category, list):
                all_terms.extend(category)
            elif isinstance(category, str):
                all_terms.append(category)
        
        # Filter out terms that are too short and skip the time_references field
        keywords = [term for term in all_terms if term and len(term) > 2 and term != "time_references"]
        
        # If both keywords and time constraints exist, use combined search
        if keywords and time_constraints and (time_constraints.get("start_time") or time_constraints.get("end_time")):
            all_matches = []
            seen_ids = set()
            
            for keyword in keywords:
                matches = self.db.get_clips_by_keyword_and_time(
                    keyword,
                    time_constraints.get("start_time"),
                    time_constraints.get("end_time")
                )
                for match in matches:
                    if match["id"] not in seen_ids:
                        all_matches.append(match)
                        seen_ids.add(match["id"])
            
            return all_matches
        
        # If only time constraints exist
        elif time_constraints and (time_constraints.get("start_time") or time_constraints.get("end_time")):
            return self.db.get_clips_by_timeframe(
                time_constraints.get("start_time", "1970-01-01 00:00:00"),
                time_constraints.get("end_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
        
        # If no valid keywords and no time constraints, return empty list
        elif not keywords:
            return []
        
        # Otherwise use the original keyword-only search
        else:
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