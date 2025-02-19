import cv2
import os
import time
from datetime import datetime
from supabase_init1 import upload_to_supabase

def capture_and_upload(supabase):
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR! Couldn't open webcam")
        return

    frame_interval = 10  
    check_interval = 0.1  
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  
    c_count = 1  

    while True:
        file_name = f"clip_{c_count}.jpg"
        file_path = f"/tmp/{file_name}"  

        ret, frame = cap.read()
        if not ret:
            print("ERROR! Failed to capture frame")
            break
        
        cv2.imwrite(file_path, frame)  

        # Upload to Supabase
        upload_to_supabase(supabase, file_path, session_timestamp, file_name)
        
        os.remove(file_path)  
        cv2.imshow("Captured Frame", frame)
        
        elapsed_time = 0
        while elapsed_time < frame_interval:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return session_timestamp
            time.sleep(check_interval)
            elapsed_time += check_interval

        c_count += 1  

    cap.release()
    cv2.destroyAllWindows()
    return session_timestamp