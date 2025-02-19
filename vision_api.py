from huggingface_hub import InferenceClient


#code from generates only basic description, needs to be edited based on user needs.
def get_image_description(api_key, image_url):
    client = InferenceClient(
        provider="hf-inference",
        api_key=api_key
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image. "},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }
    ]

    completion = client.chat.completions.create(
        model="meta-llama/Llama-3.2-11B-Vision-Instruct",
        messages=messages,
        max_tokens=500
    )

    return completion.choices[0].message.content  