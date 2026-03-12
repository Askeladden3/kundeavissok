from google import genai
from google.genai import types
from pydantic import BaseModel
from enum import Enum
import json

def categorize_deals(file_dir, MODEL_ID):
    "Legger til kategori i hver entry i et JSON-objekt og returnerer oppdatert JSON-objekt"

    class Category(str, Enum):
        MEAT = "meat"
        DAIRY = "dairy"
        BAKERY = "bakery"
        SEAFOOD = "seafood"
        CANDY = "candy"
        FRUIT = "fruit"
        OTHER = "other"

    class FoodItem(BaseModel):
        name: str
        category: Category

    class CategorizationResponse(BaseModel):
        items: list[FoodItem]

    prompt = "You are a grocery categorization assistant. Categorize the following list of Norwegian food item into categories provided in the schema."
    client = genai.Client()


    with open(file_dir, 'r', encoding='utf-8') as fil:
        data = json.load(fil)
    food_items = list()
    for row in data:
        food_items.append(row['name'])


    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[prompt,food_items],
        config={'response_mime_type':"application/json",
                "response_schema": CategorizationResponse}
    )

    categorized_data = response.parsed
    for idx, item in enumerate(categorized_data.items):
        data[idx]['category'] = item.category.value
    
    return data



MODEL_ID = "gemini-2.5-flash"
print(categorize_deals('temp_output\price_deals.json', MODEL_ID))