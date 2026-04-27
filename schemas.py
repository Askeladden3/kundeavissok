from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal
from enum import Enum


class flyer_category(str, Enum):
    MEAT = "meat"
    BREAD_TOPPINGS = "bread_toppings"
    DAIRY = "dairy"
    EGGS = "eggs"
    BAKERY = "bakery"
    SEAFOOD = "seafood"
    SNACKS_CANDY = "snacks_candy"
    PIZZA = "pizza"
    SODA = "soda"
    PRODUCE = "produce"
    OTHER = "other"

class flyer_unit(str, Enum):
    STK = "stk"
    ML = "ml"
    L = "L"
    G = "g"
    KG = "kg"

class base_deal(BaseModel):
    image_index : int = Field(description="Index of image item is from. Always provided in prompt.")
    name: str = Field(description="Product name. Do not include amount or numbers here.")
    total_mass: Optional[float] = Field(default=None, description='Total weight/volume')
    unit: Optional[flyer_unit] = Field(default=None, description='"stk", "kg", "g", "ml" or "l"')
    store: str = Field(description="Store that sells the items in image. Always provided in prompt.")
    brand : Optional[str] = Field(default=None, description= "If there is an identifiable brand connected to this item write it here. Otherwise, leave null.")
    category: flyer_category = Field(description="Categorize the item based on its visual appearance and name.")
    protein_type: Optional[Literal["beef", "pork", "poultry", "lamb", "mixed", "plant_based"]] = Field(
    default=None, 
    description="If the item is RAW_MEAT or BREAD_TOPPINGS containing meat, identify the primary protein. Otherwise, leave null.")

class standard_deal(base_deal):
    deal_type : Literal["standard_deal"] = Field(description = "Fixed label, do not look for this in text.")
    price_per_flyer_unit: float = Field(description='price per kg or liter.')
    total_price: float = Field(description='Total sale price (decimal)')

class percentage_deal(base_deal):
    deal_type : Literal["percentage_deal"] = Field(description = "Fixed label, do not look for this in text.")
    percentage_off : int = Field(description="Discount percentage")

class bogo_deal(base_deal):
    deal_type : Literal["bogo_deal"] = Field(description = "Fixed label, do not look for this in text.")
    items_received: int = Field(description="Total number of items the customer gets (e.g., 3 in '3 for 2').")
    items_paid_for: int = Field(description="Number of items the customer actually pays for (e.g., 2 in '3 for 2').")

class flyer_batch(BaseModel):
    flyers: List[Union[standard_deal, percentage_deal, bogo_deal]]

class restaurant_national_stores(str, Enum):
    peppes_pizza = "Peppes Pizza"
    pizzabakeren = "Pizzabakeren"
    dominos = "Dominos"

class restaurant_trondheim_stores(restaurant_national_stores):
    superhero_pizza = "Super Hero Pizza"
    
