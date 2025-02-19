from Supabase_init2 import get_supabase_client
from clip_capture import capture_and_upload
from supabase_init1 import fetch_uploaded_files, insert_into_database
from vision_api import get_image_description

supabase = get_supabase_client()

# uploading clips to supabase bucket
session_timestamp = capture_and_upload(supabase)

# description generation
if session_timestamp:
    uploaded_files = fetch_uploaded_files(supabase, session_timestamp)

    if uploaded_files:
        for file_name, public_url in uploaded_files:
            description = get_image_description("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", public_url)
            insert_into_database(supabase, file_name, public_url, description)
    else:
        print("No images found to process.")
else:
    print("No session data available.")