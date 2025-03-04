# db_connector.py
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

class SupabaseConnector:
    def __init__(self):
        """Initialize connection to Supabase"""
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def get_all_clips(self):
        """Retrieve all clips from the database"""
        response = self.client.table("todos").select("id, Clip_Name, Clip_URL, Clip_Description").execute()
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error fetching clips: {response.error}")
        
        return response.data
    
    def get_clips_by_keyword(self, keyword):
        """Retrieve clips that match a simple keyword search"""
        response = self.client.table("todos").select("id, Clip_Name, Clip_URL, Clip_Description").ilike("Clip_Description", f"%{keyword}%").execute()
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error in keyword search: {response.error}")
        
        return response.data