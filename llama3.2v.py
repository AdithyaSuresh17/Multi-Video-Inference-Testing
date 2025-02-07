from huggingface_hub import InferenceClient
import os
import time
from datetime import datetime
from main import get_supabase_client


##PULLING FROM BUCKET
supabase = get_supabase_client()
response = supabase.storage.from_("videostorage").get_public_url(
  "dearsanta.png"
)
str(response)
response=response[:-1]

##Inference api
client = InferenceClient(
	provider="hf-inference",
	api_key="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"
)

messages = [
	{
		"role": "user",
		"content": [
			{
				"type": "text",
				"text": "Describe this image in one sentence."
			},
			{
				"type": "image_url",
				"image_url": {
					"url": response
				}
			}
		]
	}
]

completion = client.chat.completions.create(
    model="meta-llama/Llama-3.2-11B-Vision-Instruct",
	messages=messages,
	max_tokens=500
)

print(completion.choices[0].message)