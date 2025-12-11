import os
import json
import base64
import time
import requests
import sys
from bs4 import BeautifulSoup
import numpy as np
import math


def Gemini_parser(BUTIKKER, DATO, add_tmp_json=False, batch_processing=True, batchsize = 14):
    '''Sender API-calls for å ekstrahere matvarer fra kundeavisene'''

    current_date, år, UKE = DATO
    API_KEY = os.getenv("GEMINI_API_KEY")


    max_retries = 3
    required_keys = ['price_deals', 'percentage_deals', 'three_for_two_deals', 'multibuy_for_price_deals', 'kroner_off_deals']

    if not API_KEY:
        sys.exit("❌ ERROR: API_KEY not found in environment variables!")
    else:
        print("✅ API_KEY is present (value hidden).")

    IMAGE_INPUT_FOLDER = f"temp_output/bilder" 
    JSON_OUTPUT_FOLDER = "temp_output/results_JSON"

    try:
        os.mkdir(JSON_OUTPUT_FOLDER)
    except:
        pass



    class API_model():

        def __init__(self, id, name, RPM, rateLimit, api_url):
            ModelData = ModelData[id]
            self.id = id
            self.name = name
            self.n_calls = 0
            self.is_exhausted = False
            self.RPM = RPM
            self.sleeptime = 60 // self.RPM
            self.rate_limit = rateLimit
            self.api_url = api_url

        def rate_limit_reached(self):
            if self.n_calls > self.rate_limit:
                self.is_exhausted = True
                return True
            else:
                return False

    flash_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    pro_api_url =   f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={API_KEY}'

    Gem_flash = API_model('flash', 'Gemini Flash', 10, 250, flash_api_url)
    Gem_pro = API_model('pro', 'Gemini Pro', 2, 50, pro_api_url)

    
    def save_to_json(data, filename):
        """Saves a list of data to a JSON file if the list is not empty."""
        if data:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                print(f"Successfully saved {len(data)} items to '{filename}'.")
            except IOError as e:
                print(f"Error writing to output file '{filename}': {e}")
        else:
            print(f"No data to save for '{filename}'. File not created.")

    def analyze_flyer_batch(flyer_batch, model):
        image_parts = []
    
        # Går igjennom hver flyer-objekt i listen og legger til bildedata
        for flyer_page in flyer_batch:
            try:
                with open(flyer_page.img_path, "rb") as image_file:
                    # Standardize mimeType if needed, or detect dynamically
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    image_parts.append({
                        "inlineData": {
                            "mimeType": "image/jpeg", # Ensure this matches your files (png/jpeg)
                            "data": image_data
                        }
                    })
            except IOError as e:
                print(f"Skipping file due to error: {flyer_page.img_path} - {e}")
                continue

        if not image_parts:
            print("No valid images to process.")
            return None


        prompt = """
        Analyze the provided images of Norwegian grocery store flyers. Process each image independently in the order they are provided.
        
        Your goal is to identify deals, focusing on **price per kilogram (pr. kg) or price per liter (pr. l)**, which is often in smaller text below the product description.

        **OUTPUT FORMAT:**
        Return a single valid **JSON Array** (list). 
        Each item in the array must correspond to one image and contain the following fields:
        - `image_index`: The sequential number of the image (0, 1, 2...).
        - `deals`: A JSON array containing the five categorized deal types below.

        **DEAL CATEGORIES (inside the `deals` object):**
        
        1.  `price_deals`: Standard price reductions.
            - `name`: Product name.
            - `price_per_unit`: **The most important value.** (decimal). Look for "pr. kg" or "pr. l".
            - `total_price`: Total sale price (decimal).
            - `total_mass`: Total weight/volume (decimal, e.g. 0.5 for 500g), or null.
            - `unit`: "kg" or "l".

        2.  `percentage_deals`: Percentage off (e.g., "-30%").
            - `name`: Product name.
            - `percentage_off`: Discount percentage (number).

        3.  `three_for_two_deals`: ONLY "3 for 2" offers.
            - `name`: Product name.

        4.  `multibuy_for_price_deals`: "X for Y kr" offers (NOT "3 for 2").
            - `name`: Product name.
            - `amount_of_wares`: Number of items (X).
            - `set_price`: Total price (Y).

        5.  `kroner_off_deals`: Fixed amount subtracted (e.g., "-5 kr").
            - `name`: Product name.
            - `amount_subtracted`: Amount subtracted (number).

        Do not include any text or markdown outside the JSON Array.
        """

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}] + image_parts 
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                # Optional: Increase token count if batch size is large
                # "maxOutputTokens": 8192 
            }
        }

        headers = {'Content-Type': 'application/json'}

        for attempt in range(max_retries):


            model.n_calls += 1

            try:
                response = requests.post(model.api_url, headers=headers, json=payload, timeout=90)
                response.raise_for_status()
                
                extracted_data = response.json()
                
                json_text = extracted_data['candidates'][0]['content']['parts'][0]['text']
                categorized_deals = json.loads(json_text)

                for flyer_content in categorized_deals:
                    i = flyer_content['image_index']
                    flyer_batch[i].AI_model_used = model.id
                    if all(k in flyer_content['deals'] for k in required_keys):
                        flyer_batch[i].categorized_deal = flyer_content['deals']
                    else:
                        print(f'\nUgyldig struktur på følgende bilde: {flyer_batch[i].img_path}. Hoppes over.')
                print(f'\nDeals successfully extracted from batch ({flyer_batch[0].store} | {flyer_batch[-1].store})\n')
                return None

            except requests.exceptions.RequestException as e:
                print(f"  API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                #Hvis APIen sender kode 429 ("Rate limit reached") så skal modellen byttes
                if e.response is not None and e.response.status_code == 429:
                    model.is_exhausted = True
                    print(f"Error 429 motatt. Slutter nå å bruke {model.name}.")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    print(f"  Final API request failed. Response: {response.text if 'response' in locals() else 'No response'}")
                    return None
            except (KeyError, IndexError, json.JSONDecodeError, ValueError) as e:
                print(f"  Error parsing API response (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"  Received data: {response.text if 'response' in locals() else 'No response'}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return None
                
        return None
        

    def analyze_flyer(flyer, model):
        """
        Analyzes a single flyer image using the Gemini API and returns structured data.
        """
        print(f"Processing image: {flyer.img_path}...")

        try:
            with open(flyer.img_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
        except IOError as e:
            print(f"  Error reading file: {e}")
            return None

        prompt = """
        Analyze the provided image of a Norwegian grocery store flyer. Your primary goal is to identify the best deals by focusing on the **price per kilogram (pr. kg) or price per liter (pr. l)**, which is often in smaller text below the product description.

        Identify and categorize all distinct product offers into five specific types.
        Return the result as a single, valid JSON object with five keys. Each key should contain an array of objects for that category. If a category has no offers, its array must be empty.

        1.  `price_deals`: Standard price reductions.
            - `name`: The main name of the product.
            - `price_per_unit`: **The most important value.** The price per kg or liter, as a decimal number. Find this by looking for text like "pr. kg" or "pr. l".
            - `total_price`: The total sale price as a decimal number.
            - `total_mass`: The total weight/volume as a decimal number (e.g., "500 g" becomes 0.5, "1.5 l" becomes 1.5), or null.
            - `unit`: The unit of measurement, either "kg" or "l". Infer from the product type or the unit price text.

        2.  `percentage_deals`: A percentage off the price (e.g., "-30%").
            - `name`: The product name.
            - `percentage_off`: The discount percentage as a number (e.g., 30).

        3.  `three_for_two_deals`: ONLY for "3 for 2" offers. Do not include any other combinations.
            - `name`: The product name.

        4.  `multibuy_for_price_deals`: For offers like "X for Y kr" that are NOT "3 for 2".
            - `name`: The product name.
            - `amount_of_wares`: The number of items you must buy (the 'X' value).
            - `set_price`: The total price for the multibuy (the 'Y' value).

        5.  `kroner_off_deals`: A fixed amount subtracted from the price (e.g., "-5 kr").
            - `name`: The product name.
            - `amount_subtracted`: The amount of kroners subtracted as a number (e.g., 5).

        Do not include any text, markdown, or explanations outside of the final JSON object.
        """

        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": image_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
            }
        }

        headers = {'Content-Type': 'application/json'}

        max_retries = 3

        for attempt in range(max_retries):


            model.n_calls += 1

            try:
                response = requests.post(model.api_url, headers=headers, json=payload, timeout=90)
                response.raise_for_status()
                
                extracted_data = response.json()
                
                json_text = extracted_data['candidates'][0]['content']['parts'][0]['text']
                categorized_deals = json.loads(json_text)

                if all(k in categorized_deals for k in required_keys):
                    print(f"  Successfully extracted deals from the image.")
                    flyer.categorized_deal = categorized_deals
                    return categorized_deals
                else:
                    raise ValueError("Response JSON is missing one or more required keys.")

            except requests.exceptions.RequestException as e:
                print(f"  API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                #Hvis APIen sender kode 429 ("Rate limit reached") så skal modellen byttes
                if e.response is not None and e.response.status_code == 429:
                    model.is_exhausted = True
                    print(f"Error 429 motatt. Slutter nå å bruke {model.name}.")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    print(f"  Final API request failed. Response: {response.text if 'response' in locals() else 'No response'}")
                    return None
            except (KeyError, IndexError, json.JSONDecodeError, ValueError) as e:
                print(f"  Error parsing API response (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"  Received data: {response.text if 'response' in locals() else 'No response'}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return None
                
        return None


    def process_all_flyers():
        """
        Main function to loop through all images, process them, and save the
        consolidated results to multiple JSON files based on deal type.
        """

        class flyer():
            '''Generell flyer-klasse. Tar inn store, acquired_date, page_number, category_key og img_path.
            
            Har metode for å produsere ferdig "deals"-objekt som kan videresendes til save_json
            '''

            def __init__(self, prop):
                self.store = prop['store']
                self.acquired_date = prop['acquired_date']
                self.page_number = prop['page_number']
                self.img_path = prop['img_path']

            def create_dealsobj(self):
                processed_deals = {}
                if hasattr(self, 'categorized_deal'):
                    if self.categorized_deal:
                        for category_key, category_deals in self.categorized_deal.items():
                            processed_deals[category_key] = []
                            for deal in category_deals:
                                deal['store'] = self.store
                                deal['acquired_date'] = self.acquired_date
                                deal['page_number'] = self.page_number
                                deal['AI_model_used'] = None if not hasattr(self, 'AI_model_used') else self.AI_model_used
                                processed_deals[category_key].append(deal)
                        return processed_deals
                return None
            
        
        all_deals = {
                'price_deals': [],
                'percentage_deals': [],
                'three_for_two_deals': [],
                'multibuy_for_price_deals': [],
                'kroner_off_deals': []
            }

        if add_tmp_json:

            json_url = "https://askhf.folk.ntnu.no/temp_JSON/"


            response = requests.get(json_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all("a"):
                href = link.get("href")
                if href and href.endswith(".json"):
                    file_url = json_url + href
                    r = requests.get(file_url)
                    with open(f'{JSON_OUTPUT_FOLDER}/{href}', "wb") as f:
                        f.write(r.content)

            for category in all_deals.keys():
                with open(f'{JSON_OUTPUT_FOLDER}/{category}.json', 'r', encoding='utf-8') as f:
                    all_deals[category] = json.load(f)

            print(f"Antall entries i price_deals er {len(all_deals['price_deals'])}. Ser det rett ut? \n\n")
            time.sleep(5)

        
        if not os.path.exists(IMAGE_INPUT_FOLDER):
            print("Please add your flyer images to folder and run the script again.")
            sys.exit()

        if not os.path.exists(JSON_OUTPUT_FOLDER):
            print(f"Creating output folder: {JSON_OUTPUT_FOLDER}")
            os.makedirs((JSON_OUTPUT_FOLDER))
            print("Output folder created. Continuing.")
        else:
            print(f"file path {JSON_OUTPUT_FOLDER} already exists, continuing script... \n")


        batch_image_dict = dict()
        full_flyer_list = list()
        image_files = []
        for f in os.listdir(IMAGE_INPUT_FOLDER):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                for shop in BUTIKKER:
                    if shop in f:
                        prop = {
                            'store': shop,
                            'acquired_date': current_date.date().strftime(r'%d-%m-%Y'),
                            'page_number': f.split('_')[-1].split('.')[0],
                            'img_path': os.path.join(IMAGE_INPUT_FOLDER, f)
                            }
                        
                        curr_flyer = flyer(prop)
                        if shop in batch_image_dict:
                            batch_image_dict[shop].append(curr_flyer)
                        else:
                            batch_image_dict[shop] = [curr_flyer]
                        full_flyer_list.append(curr_flyer)
                        image_files.append(f)
                        break

        if not image_files:
            print(f"No image files found in '{IMAGE_INPUT_FOLDER}'.")
            return
        

        print(f"{len(image_files)} bilder skal behandles.")
        model = Gem_flash


        if batch_processing:
            batched_flyer_list = np.array_split(full_flyer_list, math.ceil(len(full_flyer_list)/batchsize))
            for flyer_batch in batched_flyer_list:
                analyze_flyer_batch(flyer_batch, model)
                for flyer in flyer_batch:
                    processed_deal = flyer.create_dealsobj()
                    if processed_deal:
                        for category_key, deals_list in processed_deal.items():
                            if category_key in all_deals:
                                for deal in deals_list:
                                    all_deals[category_key].append(deal)
                print("  Saving current progress to files...")
                for category_key, deals_list in all_deals.items():
                    save_to_json(deals_list, f"{JSON_OUTPUT_FOLDER}/{category_key}.json")


        else:
            for store, flyer_batch in batch_image_dict.items():
                print(f'Analyserer nå butikken: {store}')
                for flyer in flyer_batch:
                    analyze_flyer(flyer, model)
                    if hasattr(flyer, "categorized_deal") and flyer.categorized_deal:
                        time_prev = time.perf_counter()


                        processed_deal = flyer.create_dealsobj()
                        for category_key, deals_list in processed_deal.items():
                            if category_key in all_deals:
                                for deal in deals_list:
                                    all_deals[category_key].append(deal)
                        print("  Saving current progress to files...")
                        for category_key, deals_list in all_deals.items():
                            save_to_json(deals_list, f"{JSON_OUTPUT_FOLDER}/{category_key}.json")



                        time_new = time.perf_counter()
                        analysis_time = time_new - time_prev
                        if analysis_time < model.sleeptime:
                            time.sleep(model.sleeptime - analysis_time)
                            print(f'API is analyzing too quickly. Have to sleep for {model.sleeptime - analysis_time :.3f}s')

        print("\nProcessing complete.")


    process_all_flyers()