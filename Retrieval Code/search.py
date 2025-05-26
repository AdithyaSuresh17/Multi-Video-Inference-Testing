# search_engine.py
from db import SupabaseConnector
from llm_process import QueryProcessor
from config import RELEVANCE_THRESHOLD, MAX_RESULTS
from datetime import datetime, timedelta
import json

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
        
        # Manufacturing zone keywords
        self.soldering_keywords = [
            "solder", "reflow", "wave", "flux", "temperature", "heating",
            "joint", "thermal", "profile", "paste", "wetting", "cold joint"
        ]
        
        self.pick_and_place_keywords = [
            "pick", "place", "component", "placement", "alignment", "position",
            "gripper", "nozzle", "feeder", "orientation", "missing", "tilt"
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
    
    def _is_manufacturing_query(self, query):
        """Determine if the query is manufacturing-related"""
        lower_query = query.lower()
        
        # Check for explicit manufacturing prefix
        if "manufacturing" in lower_query or "monitoring" in lower_query:
            return True
            
        # Check for soldering station keywords
        if "soldering" in lower_query or "solder" in lower_query:
            return True
            
        # Check for pick and place keywords
        if "pick" in lower_query and "place" in lower_query:
            return True
            
        return False
    
    def _determine_manufacturing_zone(self, query):
        """Determine which manufacturing zone the query relates to"""
        lower_query = query.lower()
        
        # Count keywords related to each zone
        soldering_score = sum(1 for keyword in self.soldering_keywords if keyword in lower_query)
        pick_place_score = sum(1 for keyword in self.pick_and_place_keywords if keyword in lower_query)
        
        # Return the zone with the highest score
        if soldering_score > pick_place_score:
            return "CAM-01"  # Soldering station
        elif pick_place_score > soldering_score:
            return "CAM-02"  # Pick and place station
        else:
            return None  # No clear zone identified
        
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
    
    def _filter_for_manufacturing_zone(self, clips, camera_id):
        """Filter clips for a specific manufacturing zone camera"""
        if not camera_id:
            return clips
            
        return [clip for clip in clips if clip.get("camera_id") == camera_id]
    
    def _enhance_with_manufacturing_data(self, clips, query):
        """Add manufacturing-specific data to clips based on content analysis"""
        enhanced_clips = []
        
        # Determine if this is a query about issues/alerts
        is_issue_query = any(word in query.lower() for word in 
                            ["problem", "issue", "defect", "error", "alert", "warning", 
                             "critical", "failure", "fault", "malfunction"])
        
        for clip in clips:
            # Create a copy to avoid modifying the original
            enhanced_clip = clip.copy()
            
            # Default values
            enhanced_clip["zone_type"] = None
            enhanced_clip["alert_level"] = "normal"
            enhanced_clip["issue_type"] = None
            enhanced_clip["process_parameters"] = None
            
            description = clip.get("image_description", "").lower()
            camera_id = clip.get("camera_id")
            
            # Determine zone type based on camera ID
            if camera_id == "CAM-01":
                enhanced_clip["zone_type"] = "Soldering Station"
            elif camera_id == "CAM-02":
                enhanced_clip["zone_type"] = "Pick-and-Place"
            
            # Determine alert level based on description
            if any(word in description for word in ["critical", "severe", "urgent", "emergency", "failure"]):
                enhanced_clip["alert_level"] = "critical"
            elif any(word in description for word in ["warning", "caution", "attention", "issue", "problem"]):
                enhanced_clip["alert_level"] = "warning"
            
            # Determine issue type based on camera ID and description
            if camera_id == "CAM-01":  # Soldering station
                if "cold" in description and "solder" in description:
                    enhanced_clip["issue_type"] = "cold solder joint"
                elif "bridge" in description:
                    enhanced_clip["issue_type"] = "solder bridge"
                elif "insufficient" in description:
                    enhanced_clip["issue_type"] = "insufficient solder"
                elif "excessive" in description:
                    enhanced_clip["issue_type"] = "excessive solder"
                elif "temperature" in description:
                    enhanced_clip["issue_type"] = "temperature issue"
            elif camera_id == "CAM-02":  # Pick-and-Place
                if "misaligned" in description:
                    enhanced_clip["issue_type"] = "misaligned component"
                elif "missing" in description:
                    enhanced_clip["issue_type"] = "missing component"
                elif "foreign" in description or "debris" in description:
                    enhanced_clip["issue_type"] = "foreign object debris"
                elif "tilt" in description:
                    enhanced_clip["issue_type"] = "tilted component"
            
            # Generate sample process parameters based on zone
            if camera_id == "CAM-01":  # Soldering station
                # Generate some sample temperature values that might be related to issues in the description
                temp_value = "210°C"
                if "cold" in description:
                    temp_value = "185°C (Low)"
                elif "excessive" in description or "overheat" in description:
                    temp_value = "245°C (High)"
                
                enhanced_clip["process_parameters"] = json.dumps({
                    "temperature": temp_value,
                    "speed": "30 cm/min",
                    "pressure": "0.5 MPa",
                    "duration": "45 sec"
                })
            elif camera_id == "CAM-02":  # Pick-and-Place
                enhanced_clip["process_parameters"] = json.dumps({
                    "speed": "2500 cph",
                    "pressure": "0.3 MPa",
                    "temperature": "24°C",
                    "duration": "0.8 sec/component"
                })
            
            # For issue queries, prioritize clips that have issues
            if is_issue_query and enhanced_clip["alert_level"] != "normal":
                # Boost relevance for issue-related results in issue queries
                enhanced_clip["relevance_score"] = enhanced_clip.get("relevance_score", 0.8) * 1.2
                # Cap at 1.0
                if enhanced_clip["relevance_score"] > 1.0:
                    enhanced_clip["relevance_score"] = 1.0
            
            enhanced_clips.append(enhanced_clip)
        
        return enhanced_clips
    def _get_latest_clips(self, query):
        """Get the most recent clips from the database"""
        try:
            # Get all clips with timestamp
            all_clips = self.db.get_all_clips()
            
            if not all_clips:
                return []
            
            # Check for query types
            is_pcb_query = self._is_pcb_query(query)
            is_manufacturing_query = self._is_manufacturing_query(query)
            manufacturing_zone = self._determine_manufacturing_zone(query) if is_manufacturing_query else None
            
            # Apply appropriate filters based on query type
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
            
            elif is_manufacturing_query:
                # First filter by manufacturing zone if specified
                if manufacturing_zone:
                    all_clips = self._filter_for_manufacturing_zone(all_clips, manufacturing_zone)
                
                # Then look for specific manufacturing issue types
                if "solder" in query.lower() or "temperature" in query.lower() or "heat" in query.lower():
                    print("Filtering for soldering-related issues")
                    filtered_clips = []
                    for clip in all_clips:
                        description = clip.get("image_description", "").lower()
                        if any(word in description for word in self.soldering_keywords):
                            filtered_clips.append(clip)
                    
                    if filtered_clips:
                        all_clips = filtered_clips
                
                elif "missing" in query.lower() or "component" in query.lower() or "alignment" in query.lower():
                    print("Filtering for pick-and-place issues")
                    filtered_clips = []
                    for clip in all_clips:
                        description = clip.get("image_description", "").lower()
                        if any(word in description for word in self.pick_and_place_keywords):
                            filtered_clips.append(clip)
                    
                    if filtered_clips:
                        all_clips = filtered_clips
            
            else:
                # For surveillance (legacy mode), filter for specific objects if mentioned
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
    
    def search(self, user_query):
        """Execute search for clips matching the user query including temporal aspects"""
        print(f"Processing search: '{user_query}'")
        
        # Check query type
        is_pcb_query = self._is_pcb_query(user_query)
        is_manufacturing_query = self._is_manufacturing_query(user_query)
        
        # Determine manufacturing zone if applicable
        manufacturing_zone = None
        if is_manufacturing_query:
            manufacturing_zone = self._determine_manufacturing_zone(user_query)
            print(f"Manufacturing zone identified: {manufacturing_zone}")
        
        print(f"PCB-related query: {is_pcb_query}")
        print(f"Manufacturing-related query: {is_manufacturing_query}")
        
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
            
            # For manufacturing queries, filter for zone if specified
            if is_manufacturing_query and manufacturing_zone and latest_clips:
                latest_clips = self._filter_for_manufacturing_zone(latest_clips, manufacturing_zone)
                print(f"After zone filtering: {len(latest_clips)} matches")
            
            if latest_clips:
                # If specifically requesting a single image, return only the most recent one
                if single_image_request:
                    print("Returning single latest image as requested")
                    result_clips = [latest_clips[0]]  # Return just the first (most recent) result
                else:
                    print(f"Returning {len(latest_clips)} latest clips")
                    result_clips = latest_clips
                
                # For manufacturing queries, enhance with manufacturing data
                if is_manufacturing_query:
                    result_clips = self._enhance_with_manufacturing_data(result_clips, user_query)
                
                return result_clips
        
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
                    
                    # For PCB queries, filter for PCB-relevant results
                    if is_pcb_query:
                        potential_matches = self._filter_for_pcb_relevance(potential_matches)
                        
                    # For manufacturing queries, filter for zone if specified
                    if is_manufacturing_query and manufacturing_zone:
                        potential_matches = self._filter_for_manufacturing_zone(potential_matches, manufacturing_zone)
                        
                    # Skip to ranking if we have matches
                    # Skip ranking for date-based searches - directly return results
                    if potential_matches:
                        print(f"Bypassing ranking for date-specific search, returning {len(potential_matches)} results directly")
                        # Format results with default high relevance score
                        for match in potential_matches:
                            match["relevance_score"] = 0.95  # Set a high default relevance
                        
                        # For manufacturing queries, enhance with manufacturing data
                        if is_manufacturing_query:
                            potential_matches = self._enhance_with_manufacturing_data(potential_matches, user_query)
                            
                        # Limit number of results
                        results = potential_matches[:self.max_results]
                        return results
        
        # Standard search flow if not a full day search or if full day search found no results
        if not potential_matches:  # Only proceed if potential_matches is still empty
            potential_matches = self._get_potential_matches(search_terms, time_constraints)
            print(f"Found {len(potential_matches)} potential matches")
        
        # Apply mode-specific filtering
        if is_pcb_query:
            potential_matches = self._filter_for_pcb_relevance(potential_matches)
            print(f"After PCB filtering: {len(potential_matches)} matches")
        elif is_manufacturing_query and manufacturing_zone:
            potential_matches = self._filter_for_manufacturing_zone(potential_matches, manufacturing_zone)
            print(f"After manufacturing zone filtering: {len(potential_matches)} matches")
        
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
            
            # Apply mode-specific filtering to time-based results
            if is_pcb_query and potential_matches:
                potential_matches = self._filter_for_pcb_relevance(potential_matches)
                print(f"After PCB filtering: {len(potential_matches)} matches")
            elif is_manufacturing_query and manufacturing_zone and potential_matches:
                potential_matches = self._filter_for_manufacturing_zone(potential_matches, manufacturing_zone)
                print(f"After manufacturing zone filtering: {len(potential_matches)} matches")
            
            # If we found time-based matches, return them with default relevance scores
            if potential_matches:
                for match in potential_matches:
                    match["relevance_score"] = 0.8  # Good default relevance for time-based matches
                
                # For manufacturing queries, enhance with manufacturing data
                if is_manufacturing_query:
                    potential_matches = self._enhance_with_manufacturing_data(potential_matches, user_query)
                
                results = potential_matches[:self.max_results]
                return results
        
        # If still no matches, try with all clips
        if not potential_matches:
            print("No matches with constraints, trying with all clips")
            potential_matches = self.db.get_all_clips()
            
            # Apply mode-specific filtering
            if is_pcb_query and potential_matches:
                potential_matches = self._filter_for_pcb_relevance(potential_matches)
                print(f"After PCB filtering: {len(potential_matches)} matches")
            elif is_manufacturing_query and manufacturing_zone and potential_matches:
                potential_matches = self._filter_for_manufacturing_zone(potential_matches, manufacturing_zone)
                print(f"After manufacturing zone filtering: {len(potential_matches)} matches")
        
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
        
        # Include context based on query type
        if is_pcb_query and not enhanced_query.lower().startswith("pcb"):
            enhanced_query = f"PCB inspection: {enhanced_query}"
        elif is_manufacturing_query:
            if manufacturing_zone == "CAM-01" and not "soldering" in enhanced_query.lower():
                enhanced_query = f"Soldering station monitoring: {enhanced_query}"
            elif manufacturing_zone == "CAM-02" and not "pick" in enhanced_query.lower():
                enhanced_query = f"Pick-and-Place station monitoring: {enhanced_query}"
            else:
                enhanced_query = f"Manufacturing monitoring: {enhanced_query}"
        
        print(f"Enhanced query for ranking: {enhanced_query}\n")
        
        # Rank results by semantic relevance
        ranked_results = self.processor.rank_clips(
            enhanced_query, 
            potential_matches,
            self.threshold
        )
        print(f"Ranking returned {len(ranked_results)} results\n")
        
        # For manufacturing queries, enhance with manufacturing data
        if is_manufacturing_query:
            ranked_results = self._enhance_with_manufacturing_data(ranked_results, user_query)
        
        # Limit number of results
        results = ranked_results[:self.max_results] if len(ranked_results) > self.max_results else ranked_results
        
        # Debug output
        print(f"Final results count: {len(results)}")
        
        return results