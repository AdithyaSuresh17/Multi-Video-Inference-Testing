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
        
        # PCB-related keywords for filtering
        self.pcb_keywords = [
            "pcb", "circuit board", "printed circuit", "component", "solder", 
            "capacitor", "resistor", "microchip", "ic", "integrated circuit",
            "transistor", "diode", "inductor", "connector", "trace", "via",
            "bridge", "short", "missing", "misaligned", "defect", "assembly",
            "inspection", "quality", "manufacturing", "electronic", "board"
        ]
    
    def _is_pcb_query(self, query):
        """Determine if the query is PCB-related"""
        lower_query = query.lower()
        
        # Check for explicit PCB inspection prefix
        if lower_query.startswith("pcb inspection:"):
            return True
            
        # Check if query contains PCB-related keywords
        for keyword in self.pcb_keywords[:5]:  # Use the first few most distinctive keywords
            if keyword in lower_query:
                return True
                
        return False
        
    def _filter_for_pcb_relevance(self, clips):
        """Filter clips to only include PCB-relevant ones"""
        pcb_relevant_clips = []
        
        for clip in clips:
            description = clip.get("image_description", "").lower()
            
            # Check if the description contains PCB-related terms
            is_relevant = any(keyword in description for keyword in self.pcb_keywords)
            
            if is_relevant:
                pcb_relevant_clips.append(clip)
                
        return pcb_relevant_clips
    
    def search(self, user_query):
        """Execute search for clips matching the user query including temporal aspects"""
        print(f"Processing search: '{user_query}'")
        
        # Check if this is a PCB-related query
        is_pcb_query = self._is_pcb_query(user_query)
        print(f"PCB-related query: {is_pcb_query}")
        
        # Check for "latest" or "most recent" queries
        lower_query = user_query.lower()
        if any(term in lower_query for term in ["latest", "most recent", "newest", "last"]):
            print("Detected request for latest images")
            
            # Check if the user is asking for a single image
            single_image_request = any(term in lower_query for term in ["image", "picture", "photo", "snapshot", "frame"])
            
            # Get the latest matches
            latest_clips = self._get_latest_clips(lower_query)
            
            # For PCB queries, filter for PCB-relevant results
            if is_pcb_query and latest_clips:
                latest_clips = self._filter_for_pcb_relevance(latest_clips)
                print(f"After PCB filtering: {len(latest_clips)} matches")
            
            if latest_clips:
                # If specifically requesting a single image, return only the most recent one
                if single_image_request:
                    print("Returning single latest image as requested")
                    return [latest_clips[0]]  # Return just the first (most recent) result
                else:
                    print(f"Returning {len(latest_clips)} latest clips")
                    return latest_clips
        
        # Regular search flow continues if not a "latest" query or if no results
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
        
        # Initialize potential_matches here
        potential_matches = []
        
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
                        
                        # If PCB query, filter for PCB-relevant results
                        if is_pcb_query:
                            potential_matches = self._filter_for_pcb_relevance(potential_matches)
                            
                        # Limit number of results
                        results = potential_matches[:self.max_results]
                        return results
        
        # Standard search flow if not a full day search or if full day search found no results
        if not potential_matches:  # Only proceed if potential_matches is still empty
            potential_matches = self._get_potential_matches(search_terms, time_constraints)
            print(f"Found {len(potential_matches)} potential matches")
        
        # If PCB query, filter for PCB-relevant results
        if is_pcb_query:
            potential_matches = self._filter_for_pcb_relevance(potential_matches)
            print(f"After PCB filtering: {len(potential_matches)} matches")
        
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
            
            print(f"Time-only search found {len(potential_matches)} matches")
            
            # If PCB query, filter for PCB-relevant results
            if is_pcb_query and potential_matches:
                potential_matches = self._filter_for_pcb_relevance(potential_matches)
                print(f"After PCB filtering: {len(potential_matches)} matches")
            
            # If we found time-based matches, return them with default relevance scores
            if potential_matches:
                for match in potential_matches:
                    match["relevance_score"] = 0.8  # Good default relevance for time-based matches
                results = potential_matches[:self.max_results]
                return results
        
        # If still no matches, try with all clips
        if not potential_matches:
            print("No matches with constraints, trying with all clips")
            potential_matches = self.db.get_all_clips()
            
            # For PCB queries, filter for PCB-relevant results
            if is_pcb_query and potential_matches:
                potential_matches = self._filter_for_pcb_relevance(potential_matches)
                print(f"After PCB filtering: {len(potential_matches)} matches")
        
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
        
        # Include PCB context if relevant
        if is_pcb_query and not enhanced_query.lower().startswith("pcb"):
            enhanced_query = f"PCB inspection: {enhanced_query}"
        
        print(f"Enhanced query for ranking: {enhanced_query}\n")
        
        # Rank results by semantic relevance
        ranked_results = self.processor.rank_clips(
            enhanced_query, 
            potential_matches,
            self.threshold
        )
        print(f"Ranking returned {len(ranked_results)} results\n")
        
        # Limit number of results
        results = ranked_results[:self.max_results] if len(ranked_results) > self.max_results else ranked_results
        
        # Debug output
        print(f"Final results count: {len(results)}")
        
        return results
    
    def _get_latest_clips(self, query):
        """Get the most recent clips from the database"""
        try:
            # Get all clips with timestamp
            all_clips = self.db.get_all_clips()
            
            if not all_clips:
                return []
            
            # Check if this is a PCB-related query
            is_pcb_query = self._is_pcb_query(query)
            
            # For PCB queries, filter for PCB-specific components
            if is_pcb_query:
                specific_object = None
                for obj in ["capacitor", "resistor", "solder", "pcb", "circuit", "component", "chip", "diode", "board"]:
                    if obj in query:
                        specific_object = obj
                        break
                
                # First filter for PCB relevance
                all_clips = self._filter_for_pcb_relevance(all_clips)
                
                # Then filter for specific component if mentioned
                if specific_object:
                    print(f"Filtering latest PCB results for '{specific_object}'")
                    filtered_clips = []
                    for clip in all_clips:
                        if specific_object in clip.get("image_description", "").lower():
                            filtered_clips.append(clip)
                    
                    if filtered_clips:
                        all_clips = filtered_clips
                    else:
                        print(f"No PCB clips found with '{specific_object}', returning general PCB clips")
            else:
                # For surveillance, filter for specific objects if mentioned
                specific_object = None
                for obj in ["person", "people", "car", "vehicle", "bike", "bicycle", "dog", "cat", "animal"]:
                    if obj in query:
                        specific_object = obj
                        break
                
                if specific_object:
                    print(f"Filtering latest results for '{specific_object}'")
                    filtered_clips = []
                    for clip in all_clips:
                        if specific_object in clip.get("image_description", "").lower():
                            filtered_clips.append(clip)
                    
                    if filtered_clips:
                        all_clips = filtered_clips
                    else:
                        print(f"No clips found with '{specific_object}', returning general latest clips")
            
            # Sort by time_created (most recent first)
            sorted_clips = sorted(
                all_clips, 
                key=lambda x: x.get("time_created", "1970-01-01 00:00:00"), 
                reverse=True
            )
            
            # Add relevance scores
            for clip in sorted_clips:
                clip["relevance_score"] = 0.95  # High score for latest clips
            
            # Return top N results
            return sorted_clips[:self.max_results]
            
        except Exception as e:
            print(f"Error getting latest clips: {e}")
            return []
    
    def _get_potential_matches(self, search_terms, time_constraints=None):
        """Get potential matches using keyword filtering and time constraints"""
        all_terms = []
        
        # Extract all keywords from search terms
        for key, value in search_terms.items():
            if key != "time_references":  # Skip time_references object
                if isinstance(value, list):
                    all_terms.extend(value)
                elif isinstance(value, str):
                    all_terms.append(value)
        
        # Filter out terms that are too short and skip the time_references field
        keywords = [term for term in all_terms if term and len(term) > 2]
        print(f"Search keywords: {keywords}")
        
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