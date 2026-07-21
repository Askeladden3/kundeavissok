import os
from openai import OpenAI
from pydantic_models import FlyerBatch

# Initialize the client with your custom backend details
client = OpenAI(
    base_url="http://100.98.148.94:8001/v1",  # Replace with your backend URL (e.g., LM Studio, Ollama, vLLM)
    api_key="bla-bla-bla"
)

try:
    # Send the chat completion request
    response = client.chat.completions.create(
        model="/models/gemma4-12B-nvfp4",  # Replace with the exact model name hosted on your backend
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Explain quantum computing in one sentence."}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "flyer_batch",
                "schema": FlyerBatch.model_json_schema()
            }
        },
        temperature=0.3

    )

    # Print the text response
    print(response.choices[0].message.content)

except Exception as e:
    print(f"An error occurred: {e}")
