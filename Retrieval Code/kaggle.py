import os
import base64
import openai
import random
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

# Target folders
FOLDERS = {
    "Missing hole": "/kaggle/input/pcb-defects/PCB_DATASET/images/Missing_hole",
    "Mouse bite": "/kaggle/input/pcb-defects/PCB_DATASET/images/Mouse_bite",
    "Open circuit": "/kaggle/input/pcb-defects/PCB_DATASET/images/Open_circuit"
}

# Function to upload image and get public URL
def upload_to_supabase(path, name):
    with open(path, "rb") as f:
        content = f.read()
    supabase.storage.from_(SUPABASE_BUCKET).upload(file=content, path=name, file_options={"content-type": "image/jpeg", "upsert": True})
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{name}"
    return public_url

# Function to generate a description using GPT-4o
def generate_description(image_path, defect_type):
    with open(image_path, "rb") as f:
        image_data = f.read()
    b64_image = base64.b64encode(image_data).decode("utf-8")
    try:
        response = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a PCB inspection expert."},
                {"role": "user", "content": f"Analyze this image showing a '{defect_type}' defect on a PCB. Provide a clear and short description of the defect."}
            ],
            temperature=0.2,
            max_tokens=100,
            tools=[{"type": "image", "format": "base64", "data": b64_image}]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error generating description: {e}")
        return f"A PCB image showing a {defect_type} defect."

# Upload + insert loop
records = []

for defect_type, folder_path in FOLDERS.items():
    files = list(Path(folder_path).glob("*.jpg"))[:50]
    for file in files:
        file_name = f"{defect_type.replace(' ', '_')}/{file.name}"
        image_url = upload_to_supabase(str(file), file_name)
        description = generate_description(str(file), defect_type)

        # Construct DB row
        record = {
            "camera_id": None,
            "base_64_image": image_url,
            "image_description": description,
            "time_created": None,  # Optional: use datetime.now().isoformat() if desired
            "zone_type": "PCB",
            "alert_level": "warning",
            "issue_type": defect_type,
            "process_parameters": None
        }
        records.append(record)

# Insert in batches
for i in range(0, len(records), 10):
    batch = records[i:i+10]
    supabase.table("todos").insert(batch).execute()
