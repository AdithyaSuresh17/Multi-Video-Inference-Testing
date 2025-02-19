import os

def upload_to_supabase(supabase, file_path, session_timestamp, file_name):
    print(f"Pushing {file_name} to bucket: ")

    with open(file_path, "rb") as f:
        supabase.storage.from_("videostorage").upload(
            f"{session_timestamp}/{file_name}", f, {"content-type": "image/jpeg"}
        )

    print(f"Uploaded: {file_name} to folder {session_timestamp}")

def fetch_uploaded_files(supabase, session_timestamp):
    file_list_response = supabase.storage.from_("videostorage").list(session_timestamp)

    file_urls = []
    if file_list_response:
        for file_info in file_list_response:
            file_name = file_info["name"]
            public_url = supabase.storage.from_("videostorage").get_public_url(f"{session_timestamp}/{file_name}").strip()
            file_urls.append((file_name, public_url))
            print(f"File: {file_name}, URL: {public_url}")
    else:
        print("No files in bucket")

    return file_urls

def insert_into_database(supabase, file_name, public_url, description):
    supabase.table("todos").insert({
        "Clip_Name": file_name,  
        "Clip_URL": public_url,
        "Clip_Description": description
    }).execute()

    print("Data successfully added to the database!")