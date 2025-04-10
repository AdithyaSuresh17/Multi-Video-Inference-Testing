# llm_processor.py
import json
from openai import OpenAI
from config import OPENAI_API_KEY, GPT_MODEL

#localhost code needs to be added
class QueryProcessor:
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = GPT_MODEL
    
    def extract_search_terms(self, user_query):
        """Extract structured search terms from user query including temporal aspects"""
        system_prompt = "You are a surveillance footage search query analyzer. Extract key visual elements and time references from the user's search query."
        
        from datetime import datetime, timedelta
        current_date = datetime.now()
        
        user_prompt = f"""
        Analyze this search query: "{user_query}"
        
        Today's date is {current_date.strftime('%Y-%m-%d')}.
        
        Extract and return a JSON object with these fields:
        - keywords: List of important words or phrases to search for
        - primary_objects: Main subjects/objects in the query
        - attributes: Descriptive attributes (colors, sizes, etc.)
        - actions: Actions or behaviors mentioned
        - time_references:  1Object with these fields:
        KEEP IN MIND: 
            - As a default if the year is not present, it will be set to 2025 for all dates
            - For relative time expressions, calculate the actual date based on today ({current_date.strftime('%Y-%m-%d')})
            - Handle time constraints like "between 12 Am and 6 PM" (meaning from 12 AM until 6 PM)
            - Handle time constraints like "before 8 PM" (meaning from start of day until 8 PM)
            - Handle time constraints like "after 3 PM" (meaning from 3 PM until end of day)
            - Convert expressions like "N days ago", "N weeks back", "N months ago" to actual dates
            - "today" means {current_date.strftime('%Y-%m-%d')}
            - "yesterday" means {(current_date - timedelta(days=1)).strftime('%Y-%m-%d')}
            - "last week" means the 7-day period ending today
            
            - specific_date: ISO date string YYYY-MM-DD if mentioned, null if not
            - specific_time: Time in 24hr format HH:MM if mentioned, null if not
            - relative_time: Original text descriptions like "yesterday", "last week", "3 days ago", etc.
            - time_period: Object with "start" and "end" fields if a range is mentioned
            - day_part: Morning/afternoon/evening/night if mentioned
        
        Return only the JSON without explanation.
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        try:
            content = response.choices[0].message.content
            # Extract JSON from response (in case model adds explanations)
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            
            return json.loads(content)
        except Exception as e:
            print(f"Error parsing search terms: {e}")
            # Fallback to basic structure
            return {
                "keywords": [word for word in user_query.split() if len(word) > 2],
                "primary_objects": [],
                "attributes": [],
                "actions": []
            }
    
    def rank_clips(self, user_query, clips, threshold=0.6):
        """Rank clips by relevance to the query"""
        if not clips:
            return []
        
        # Prepare clip data
        clip_data = []
        for clip in clips:
            clip_data.append({
                "id": clip["id"],
                "description": clip["image_description"]
            })
        
        system_prompt = """
        You are a clip search system. Evaluate how relevant each clip is to the user's search query.
        Return a JSON list of objects with id and score fields, where score is between 0 and 1.
        """
        
        user_prompt = f"""
        User search query: "{user_query}"
        
        Clips to evaluate:
        {json.dumps(clip_data)}
        
        For each clip, assign a relevance score from 0.0 to 1.0, where:
        - 1.0: Perfect match to the query
        - 0.7-0.9: Strong match with most elements present
        - 0.4-0.6: Moderate match with some elements present
        - 0.1-0.3: Weak match with few elements present
        - 0.0: No relevance to the query
        
        Return only a JSON array of objects with 'id' and 'score' fields, sorted by score in descending order.
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        try:
            content = response.choices[0].message.content
            # Extract JSON array from response
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                rankings = json.loads(json_str)
            else:
                rankings = json.loads(content)
            
            # Filter by threshold and map back to full clip data
            results = []
            for ranking in rankings:
                if ranking["score"] >= threshold:
                    for clip in clips:
                        if clip["id"] == ranking["id"]:
                            results.append({
                                **clip,
                                "relevance_score": ranking["score"]
                            })
                            break
            
            return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
        except Exception as e:
            print(f"Error ranking clips: {e}")
            print(f"Raw response: {response.choices[0].message.content}")
            return []
    def parse_time_references(self, time_refs):
        """Convert natural language time references to actual timestamps"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        result = {"start_time": None, "end_time": None}

        print(f"Parsing time references: {time_refs}")

        if time_refs.get("time_period") and isinstance(time_refs["time_period"], dict):
            period = time_refs["time_period"]
            if period.get("start"):
                result["start_time"] = period["start"]
            if period.get("end"):
                result["end_time"] = period["end"]
            return result

        # Handle specific date
        if time_refs.get("specific_date"):
            try:
                base_date = datetime.fromisoformat(time_refs["specific_date"])
                
                # If today is mentioned, use actual current date
                if time_refs.get("relative_time") and "today" in time_refs["relative_time"].lower():
                    base_date = now.replace(hour=0, minute=0, second=0)
                
                # Check for "before X time" pattern
                if time_refs.get("specific_time") and time_refs.get("relative_time") and "before" in str(time_refs.get("relative_time", "")).lower():
                    time_parts = time_refs["specific_time"].split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    
                    end_time = base_date.replace(hour=hour, minute=minute, second=0)
                    start_time = base_date.replace(hour=0, minute=0, second=0)  # Start of day
                    
                    result["start_time"] = start_time.isoformat()
                    result["end_time"] = end_time.isoformat()
                    return result
                    
                # Default time handling
                if not time_refs.get("specific_time"):
                    result["start_time"] = base_date.replace(hour=0, minute=0, second=0).isoformat()
                    result["end_time"] = base_date.replace(hour=23, minute=59, second=59).isoformat()
                else:
                    # Handle specific time on specific date
                    time_parts = time_refs["specific_time"].split(":")
                    base_date = base_date.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
                    # Default to a 1-hour window if just a specific time
                    result["start_time"] = base_date.isoformat()
                    result["end_time"] = (base_date + timedelta(hours=1)).isoformat()
            except Exception as e:
                print(f"Error parsing date: {e}")
        
        # Handle relative time references
        if time_refs.get("relative_time"):
            rel_time = time_refs["relative_time"].lower()
            if "yesterday" in rel_time:
                yesterday = now - timedelta(days=1)
                result["start_time"] = yesterday.replace(hour=0, minute=0, second=0).isoformat()
                result["end_time"] = yesterday.replace(hour=23, minute=59, second=59).isoformat()
            elif "last week" in rel_time:
                start = now - timedelta(days=7)
                result["start_time"] = start.replace(hour=0, minute=0, second=0).isoformat()
                result["end_time"] = now.isoformat()
            # Add more relative time handlers as needed
        
        # Handle day parts
        if time_refs.get("day_part") and not result["start_time"]:
            day_part = time_refs["day_part"].lower()
            base_date = now.replace(hour=0, minute=0, second=0)
            if "morning" in day_part:
                result["start_time"] = base_date.replace(hour=6).isoformat()
                result["end_time"] = base_date.replace(hour=12).isoformat()
            elif "afternoon" in day_part:
                result["start_time"] = base_date.replace(hour=12).isoformat()
                result["end_time"] = base_date.replace(hour=18).isoformat()
            elif "evening" in day_part:
                result["start_time"] = base_date.replace(hour=18).isoformat()
                result["end_time"] = base_date.replace(hour=22).isoformat()
            elif "night" in day_part:
                result["start_time"] = base_date.replace(hour=22).isoformat()
                result["end_time"] = (base_date + timedelta(days=1)).replace(hour=6).isoformat()
        
        print(f"Parsed result: {result}")
        return result