from google import genai
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal
import json
from PIL import Image

class standard_deal(BaseModel):
    deal_type : Literal["standard_deal"] = Field(description = "Fixed label, do not look for this in text.")
    name: str = Field(description="Product name.")
    price_per_unit: float = Field(description='price per kg or liter.')
    total_price: float = Field(description='Total sale price (decimal)')
    total_mass: float = Field(description='Total weight/volume')
    unit: str = Field(description='"kg", "g" or "l"')

class percentage_deal(BaseModel):
    deal_type : Literal["percentage_deal"] = Field(description = "Fixed label, do not look for this in text.")
    name: str = Field(description="Product name.")
    percentage_off : int = Field(description="Discount percentage")
    total_mass: float = Field(description='Total weight/volume')
    unit: str = Field(description='"kg", "g" or "l"')

class FlyerBatch(BaseModel):
    flyers: List[Union[standard_deal, percentage_deal]]
    index : Literal["34"] = Field(description = "Fixed value, do not change.")


prompt = """You are a grocery categorization assistant. Analyze the provided images of Norwegian grocery store flyers and find all food items on them. Process each image independently in the order they are provided.
        
        Your goal is to identify deals, focusing on **price per kilogram (pr. kg) or price per liter (pr. l)**, which is often in smaller text below the product description.
"""

client = genai.Client()
MODEL_ID = 'gemini-3.1-flash-lite-preview'

image_parts = []
bilder = [r'temp_output\bilde1.jpg', r'temp_output\bilde2.jpg', r'temp_output\bilde3.jpg', r'temp_output\bilde4.jpg']
images = list()
for img in bilder:
    images.append(Image.open(img))

response = client.models.generate_content(
    model=MODEL_ID,
    contents=[prompt,images],
    config={'response_mime_type':"application/json",
            "response_schema": FlyerBatch.model_json_schema()}
)


with open('results.json', 'w', encoding='utf-8') as fil:
    json.dump(json.loads(response.text), fil, indent=4, ensure_ascii=False)