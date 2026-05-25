from google import genai
from google.genai import errors
from PIL import Image


api_key = "AIzaSyBKCN8megAwQ7vbMznljmyBVi8J2eeNaXM"














from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal
from PIL import Image
from enum import Enum
from google.genai import types



class response_schema(BaseModel):
    url: str
    store: str

class FinalOutput(BaseModel):
    results: list[response_schema]

data_list = [
    {"store": "Bunnpris", "url": "https://etilbudsavis.no/Bunnpris?publication=XMRccRw_", "image": Image.open(r"temp_output\bilder\bunnpris1.jpg")},
    {"store": "Bunnpris", "url": "https://etilbudsavis.no/Bunnpris?publication=uZ72puyw", "image": Image.open(r"temp_output\bilder\bunnpris2.jpg")},

    {"store": "Rema", "url": "https://etilbudsavis.no/REMA-1000?publication=yP5E6BwZ", "image": Image.open(r"temp_output\bilder\Rema1.webp")},
    {"store": "Rema", "url": "https://etilbudsavis.no/REMA-1000?publication=RnkxTiTP", "image": Image.open(r"temp_output\bilder\Rema2.webp")},

    {"store": "Obs", "url": "https://etilbudsavis.no/Obs?publication=ueS-BLrr", "image": Image.open(r"temp_output\bilder\obs1.webp")},
    {"store": "Obs", "url": "https://etilbudsavis.no/Obs?publication=kE7AtTAv", "image": Image.open(r"temp_output\bilder\obs2.webp")},
    {"store": "Obs", "url": "https://etilbudsavis.no/Obs?publication=o_AhE199", "image": Image.open(r"temp_output\bilder\obs3.webp")}
]

contents = []
prompt_final = """You are a grocery flyer analyzer. You are provided with the URL and front page of multiple publications for several different stores.
Your goal is to correctly identify which URL for each store which corresponds to that weeks 'kundeavis', which is a flyer of all sales on food items for that store that week.
"""


for i, item in enumerate(data_list, start=1):
    prompt_final += f"--- Item {i} ---\nStore: {item["store"]}\nURL: {item['url']}\nImage is provided below.\n\n"
    
    # Append the PIL image directly into the contents list
    contents.append(item["image"])

# Combine the text instructions and the images into the final contents payload
final_contents = [prompt_final] + contents



with genai.Client(api_key=api_key) as client:
    response = client.models.generate_content(
    model='gemini-3.5-flash',
    contents=final_contents,
    config=types.GenerateContentConfig(
        # Enforce JSON output matching your Pydantic schema
        response_mime_type="application/json",
        response_schema=FinalOutput,
    )
    )
    print(response.text)