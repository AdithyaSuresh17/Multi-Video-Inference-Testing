import cv2
import os
import time
from datetime import datetime
from main import get_supabase_client

# Initialize Supabase client
supabase = get_supabase_client()

# Open webcam (0 = default camera)
cap = cv2.VideoCapture(0)  

# Check if camera opened successfully
if not cap.isOpened():
    print("Error: Could not open webcam")
    exit()

# Video recording settings
frame_width = int(cap.get(3))  # Width of the frame
frame_height = int(cap.get(4)) # Height of the frame
fps = 20.0  # Frames per second
video_duration = 10  # Seconds

fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4

while True:
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"video_{timestamp}.mp4"
    file_path = f"/tmp/{file_name}"  # Temporary storage (adjust for Windows)

    # Open VideoWriter to save video
    out = cv2.VideoWriter(file_path, fourcc, fps, (frame_width, frame_height))

    print(f"Recording {file_name}...")

    start_time = time.time()
    while time.time() - start_time < video_duration:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame")
            break

        out.write(frame)  # Write frame to video file

        # Display video feed (optional)
        cv2.imshow("Recording...", frame)

        # Stop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            exit()

    out.release()  # Finalize video file

    print(f"Uploading {file_name} to Supabase...")

    # Upload the recorded video
    with open(file_path, "rb") as f:
        supabase.storage.from_("videostorage").upload(file_name, f, {"content-type": "video/mp4"})
    
    print(f"Uploaded: {file_name}")

    # Delete local file after upload
    os.remove(file_path)

cap.release()
cv2.destroyAllWindows()