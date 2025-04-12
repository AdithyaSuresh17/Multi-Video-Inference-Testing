# db_connector.py
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

class SupabaseConnector:
    def __init__(self):
        """Initialize connection to Supabase"""
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def get_all_clips(self):
        """Retrieve all clips from the database"""
        response = self.client.table("todos").select("id, camera_id, base_64_image, image_description,time_created").execute()
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error fetching clips: {response.error}")
        
        return response.data
    
    def get_clips_by_keyword(self, keyword):
        """Retrieve clips that match a simple keyword search"""
        response = self.client.table("todos").select("id, camera_id, base_64_image, image_description,time_created").ilike("image_description", f"%{keyword}%").execute()
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error in keyword search: {response.error}")
        
        return response.data
    def get_clips_by_timeframe(self, start_time, end_time):
        """Retrieve clips within a specific time range"""
        # Convert ISO format to database text format by replacing 'T' with space
        db_start_time = start_time.replace('T', ' ') if start_time else None
        db_end_time = end_time.replace('T', ' ') if end_time else None
        
        print(f"Querying timeframe: {db_start_time} to {db_end_time}")
        
        response = self.client.table("todos").select("id, camera_id, base_64_image, image_description, time_created") \
            .gte("time_created", db_start_time) \
            .lte("time_created", db_end_time) \
            .execute()
        
        print(f"Timeframe query returned {len(response.data) if response.data else 0} results")
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error in timeframe search: {response.error}")
        
        return response.data
    def get_latest_clips(self, limit=10):
        """Retrieve the most recent clips from the database, ordered by time"""
        response = self.client.table("todos") \
            .select("id, camera_id, base_64_image, image_description, time_created") \
            .order("time_created", desc=True) \
            .limit(limit) \
            .execute()
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error fetching latest clips: {response.error}")
        
        return response.data


    def get_clips_by_keyword_and_time(self, keyword, start_time=None, end_time=None):
        """Retrieve clips that match both keyword and time constraints"""
        # Convert ISO format to database text format
        db_start_time = start_time.replace('T', ' ') if start_time else None
        db_end_time = end_time.replace('T', ' ') if end_time else None
        
        query = self.client.table("todos").select("id, camera_id, base_64_image, image_description, time_created") \
            .ilike("image_description", f"%{keyword}%")
        
        if db_start_time:
            query = query.gte("time_created", db_start_time)
        if db_end_time:
            query = query.lte("time_created", db_end_time)
            
        response = query.execute()
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error in combined search: {response.error}")
        
        return response.data
    def get_clips_by_date(self, date_string):
        """Retrieve clips from a specific date"""
        # For text-based date columns, we can use LIKE to find all entries on a specific date
        # Assuming the date part is always in YYYY-MM-DD format
        if len(date_string) == 10:  # Just the date part
            date_pattern = f"{date_string}%"  # e.g., "2025-04-06%"
            
            response = self.client.table("todos").select("id, camera_id, base_64_image, image_description, time_created") \
                .like("time_created", date_pattern) \
                .execute()
            
            print(f"Date pattern query for {date_pattern} returned {len(response.data) if response.data else 0} results")
            
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Error in date pattern search: {response.error}")
            
            return response.data
        else:
            # Fall back to exact time search
            return self.get_clips_by_timeframe(date_string, date_string)