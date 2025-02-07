import cv2
import os
import time
from datetime import datetime
from main import get_supabase_client

supabase = get_supabase_client()

response = supabase.storage.from_("videostorage").get_public_url(
  "dearsanta.png"
)
print(response)