# llm_processor.py
import json
from openai import OpenAI
from config import OPENAI_API_KEY, GPT_MODEL

class QueryProcessor:
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = GPT_MODEL
    
    def extract_search_terms(self, user_query):
        """Extract structured search terms from user query"""
        system_prompt = "You are a search query analyzer. Extract key visual elements from the user's search query."
        
        user_prompt = f"""
        Analyze this search query: "{user_query}"
        
        Extract and return a JSON object with these fields:
        - keywords: List of important words or phrases to search for
        - primary_objects: Main subjects/objects in the query
        - attributes: Descriptive attributes (colors, sizes, etc.)
        - actions: Actions or behaviors mentioned
        
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
                "description": clip["Clip_Description"]
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