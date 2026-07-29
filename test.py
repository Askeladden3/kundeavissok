import base64
import os
from openai import OpenAI
from pydantic_models import FlyerBatch


def encode_image_to_base64(image_path: str) -> str:
    """Reads an image file and returns a base64 Data URL."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded_string}"

with open('prompts.txt', 'r', encoding='utf-8') as f:
        prompts = f.read()
        prompts = prompts.split('/'*5)
        prompt = prompts[1]

# Initialize the client with your custom backend details
client = OpenAI(
    base_url="http://100.98.148.94:8001/v1",  # Replace with your backend URL
    api_key="bla-bla-bla",
)

# Example image paths
image_paths = ["temp_imgs/testimg.jpg"]

# Build message content list
content = [{"type": "text", "text": prompt}]
for img_path in image_paths:
    content.append(
        {
            "type": "image_url",
            "image_url": {"url": encode_image_to_base64(img_path)},
        }
    )

try:
    # Send the chat completion request
    response = client.beta.chat.completions.parse(
        model="/models/gemma4-12B-nvfp4",
        messages=[{"role": "user", "content": content}],
        response_format=FlyerBatch,
        temperature=0.3,
    )

    # Access the parsed Pydantic model response directly
    parsed_response = response.choices[0].message.parsed
    print(parsed_response)

except Exception as e:
    print(f"An error occurred: {e}")