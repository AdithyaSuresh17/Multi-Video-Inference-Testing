from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client

# Function to initialize the Supabase client
def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("Supabase URL or Key is missing in environment variables")

    return create_client(url, key)

# Ensure that if `main.py` runs as a script, it doesn't execute unnecessary code
if __name__ == "__main__":
    supabase = get_supabase_client()