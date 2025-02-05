import cv2
import os
import time
from datetime import datetime
from main import get_supabase_client

supabase = get_supabase_client()

cap = cv2.VideoCapture(0)  

if not cap.isOpened():
    print("Error: Could not open webcam")
    exit()

frame_width = int(cap.get(3))  
frame_height = int(cap.get(4)) 
fps = 20.0 
video_duration = 10  

fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # codec for MP4

while True:
    # generate  filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"video_{timestamp}.mp4"
    file_path = f"/tmp/{file_name}"  

    out = cv2.VideoWriter(file_path, fourcc, fps, (frame_width, frame_height))

    print(f"Recording {file_name}...")

    start_time = time.time()
    while time.time() - start_time < video_duration:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame")
            break

        out.write(frame)  

        cv2.imshow("Recording...", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            exit()

    out.release()  

    print(f"Uploading {file_name} to Supabase...")

    with open(file_path, "rb") as f:
        supabase.storage.from_("videostorage").upload(file_name, f, {"content-type": "video/mp4"})
    
    print(f"Uploaded: {file_name}")

    os.remove(file_path)

cap.release()
cv2.destroyAllWindows()