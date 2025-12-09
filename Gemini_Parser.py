import os
import json
import base64
import time
import datetime
from datetime import datetime
import requests
import sys
from bs4 import BeautifulSoup



def Gemini_parser(BUTIKKER, DATO, add_tmp_json=False, batch_processing=True):
    '''Sender API-calls til Gemini Flash 2.5 for å ekstrahere matvarer fra kundeavisene
    
    Har to "moduser" for å lagre data ved:

    "add" - LEGGER TIL ny data som leses fra kundeaviser på eksisterende JSON-filer 
    "replace" - SLETTER eksisterende JSON-filer og skaper nye med data som leses fra kundeaviser (standard)

    '''

    current_date, år, UKE = DATO
    max_imgs = 240

    API_KEY = os.getenv("GEMINI_API_KEY")

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

        def __init__(self, ModelData, id):
            ModelData = ModelData[id]
            self.id = id
            self.name = ModelData['name']
            self.n_calls = 0
            self.is_exhausted = False
            self.RPM = ModelData['RPM']
            self.sleeptime = 60 // self.RPM
            self.rate_limit = ModelData['rateLimit']
            self.api_url = ModelData['api_url']

        def rate_limit_reached(self):
            if self.n_calls > self.rate_limit:
                self.is_exhausted = True
                return True
            else:
                return False

    flash_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    pro_api_url =   f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={API_KEY}'

    API_model_data = {
        'pro': {'name': 'Gemini Pro', 'RPM': 2, 'rateLimit': 50, 'api_url':pro_api_url},
        'flash':   {'name': 'Gemini Flash', 'RPM': 10,  'rateLimit': 250,  'api_url':flash_api_url}
    }

    Gem_pro = API_model(API_model_data, 'pro')
    Gem_flash = API_model(API_model_data, 'flash')

    
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

    class flyer():
        '''Generell flyer-klasse. Tar inn store, acquired_date, page_number, category_key og img_path.
        
        Har metode for å produsere ferdig "deals"-objekt som videresendes til save_json
        '''

        def __init__(self, prop):
            self.store = prop['store']
            self.acquired_date = prop['acquired_date']
            self.page_number = prop['page_number']
            self.category_key = prop['category_key']
            self.img_path = prop['img_path']

        def create_dealsobj(self):
            processed_deals = {}
            if hasattr(self, 'categorized_deal') and hasattr(self, 'AI_model_used'):
                for category_key, category_deals in self.categorized_deal:
                    processed_deals[category_key] = []
                    for deal in category_deals:
                        deal['store'] = self.store
                        deal['acquired_date'] = self.acquired_date
                        deal['page_number'] = self.page_number
                        deal['AI_model_used'] = self.AI_model_used
                        processed_deals[category_key].append(deal)
                return processed_deals
            else:
                return None

    def analyze_flyer_batch(flyer_batch, model):
        image_parts = []
    
        # 1. Iterate through the list of paths and encode each image
        for flyer_page in flyer_batch:
            try:
                with open(flyer_page.img_path, "rb") as image_file:
                    # Standardize mimeType if needed, or detect dynamically
                    flyer_page.image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    image_parts.append({
                        "inlineData": {
                            "mimeType": "image/jpeg", # Ensure this matches your files (png/jpeg)
                            "data": flyer_page.image_data
                        }
                    })
            except IOError as e:
                print(f"Skipping file due to error: {flyer_page.img_path} - {e}")
                continue # Skip bad files so the batch doesn't fail entirely

        if not image_parts:
            print("No valid images to process.")
            return None

        # 2. Updated Prompt for Batch Processing
        # We explicitly ask for a JSON LIST to handle multiple outputs.
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

        # 3. Construct Payload with Prompt + All Images
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

        max_retries = 3

        for attempt in range(max_retries):


            model.n_calls += 1

            
            if model.rate_limit_reached():
                if model.id == 'pro':
                    print(f'Rate limit for Pro reached. Switching to Gemini Flash.')
                    model = Gem_flash
                elif model.id =='flash':
                    print('Rate limit for flash reached. No further images can be processed.')
                    return None


            try:
                response = requests.post(model.api_url, headers=headers, json=payload, timeout=90)
                response.raise_for_status()
                
                extracted_data = response.json()
                
                json_text = extracted_data['candidates'][0]['content']['parts'][0]['text']
                categorized_deals = json.loads(json_text)

                for i, analyzed_flyer in categorized_deals.items():
                    flyer_batch[i].categorized_deal = analyzed_flyer
                    flyer_batch[i].AI_model_used = model.id

                #TODO: Modifiser kode til å gå igjennom alle entries i json-arrayen:
                '''# Validate the structure
                required_keys = ['price_deals', 'percentage_deals', 'three_for_two_deals', 'multibuy_for_price_deals', 'kroner_off_deals']
                if all(k in categorized_deals for k in required_keys):
                    print(f"  Successfully extracted deals from the image.")
                    return categorized_deals
                else:
                    raise ValueError("Response JSON is missing one or more required keys.")'''

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
        

    def analyze_flyer_image(image_path, model):
        """
        Analyzes a single flyer image using the Gemini API and returns structured data.
        """
        print(f"Processing image: {image_path}...")

        try:
            with open(image_path, "rb") as image_file:
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

            
            if model.rate_limit_reached():
                if model.id == 'pro':
                    print(f'Rate limit for Pro reached. Switching to Gemini Flash.')
                    model = Gem_flash
                elif model.id =='flash':
                    print('Rate limit for flash reached. No further images can be processed.')
                    return None


            try:
                response = requests.post(model.api_url, headers=headers, json=payload, timeout=90)
                response.raise_for_status()
                
                extracted_data = response.json()
                
                json_text = extracted_data['candidates'][0]['content']['parts'][0]['text']
                categorized_deals = json.loads(json_text)

                # Validate the structure
                required_keys = ['price_deals', 'percentage_deals', 'three_for_two_deals', 'multibuy_for_price_deals', 'kroner_off_deals']
                if all(k in categorized_deals for k in required_keys):
                    print(f"  Successfully extracted deals from the image.")
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
            with open(f'{JSON_OUTPUT_FOLDER}/kroner_off_deals.json', 'r', encoding='utf-8') as f:
                kroner_off_deals = json.load(f)
            with open(f'{JSON_OUTPUT_FOLDER}/multibuy_for_price_deals.json', 'r', encoding='utf-8') as f:
                multibuy_for_price_deals = json.load(f)
            with open(f'{JSON_OUTPUT_FOLDER}/percentage_deals.json', 'r', encoding='utf-8') as f:
                percentage_deals = json.load(f)
            with open(f'{JSON_OUTPUT_FOLDER}/price_deals.json', 'r', encoding='utf-8') as f:
                price_deals = json.load(f)
            with open(f'{JSON_OUTPUT_FOLDER}/three_for_two_deals.json', 'r', encoding='utf-8') as f:
                three_for_two_deals = json.load(f)

            all_deals = {
                'price_deals': price_deals,
                'percentage_deals': percentage_deals,
                'three_for_two_deals': three_for_two_deals,
                'multibuy_for_price_deals': multibuy_for_price_deals,
                'kroner_off_deals': kroner_off_deals
            }

            print(f"Antall entries i price_deals er {len(price_deals)}. Ser det rett ut? \n\n")
            time.sleep(4)

            

        else:
            all_deals = {
                'price_deals': [],
                'percentage_deals': [],
                'three_for_two_deals': [],
                'multibuy_for_price_deals': [],
                'kroner_off_deals': []
            }


        
        if not os.path.exists(IMAGE_INPUT_FOLDER):
            print("Please add your flyer images to folder and run the script again.")
            sys.exit()

        if not os.path.exists(JSON_OUTPUT_FOLDER):
            print(f"Creating output folder: {JSON_OUTPUT_FOLDER}")
            os.makedirs((JSON_OUTPUT_FOLDER))
            print("Output folder created. Continuing.")
        else:
            print(f"file path {JSON_OUTPUT_FOLDER} already exists, continuing script... \n")


        image_files_dict = {}
        batch_image_dict = dict()
        image_files = []
        for f in os.listdir(IMAGE_INPUT_FOLDER):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                for shop in BUTIKKER:
                    if shop in f:
                        if shop in image_files_dict:
                            image_files_dict[shop].append(f)
                        else:
                            image_files_dict[shop] = [f]

                        prop = {
                            'store': shop,
                            'acquired_date': current_date.date(),
                            'page_number': f.split('_')[-1],
                            'img_path': f
                            }
                        if shop in batch_image_dict:
                            batch_image_dict[shop].append(flyer(prop))
                        else:
                            batch_image_dict[shop] = list(flyer(prop))
                        image_files.append(f)
                        break


        #image_files = [f for f in os.listdir(IMAGE_INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        if not image_files:
            print(f"No image files found in '{IMAGE_INPUT_FOLDER}'.")
            return
        

        print(f"{len(image_files)} bilder skal behandles.")
        model = Gem_pro



        if batch_processing:
            for store, flyer_batch in batch_image_dict:
                analyze_flyer_batch(flyer_batch)

                for flyer in flyer_batch:
                    processed_deal = flyer.create_dealsobj()
                    for category_key, deals_list in processed_deal.items():
                        if category_key in all_deals:
                            for deal in deals_list:
                                all_deals[category_key].append(deal)
                print("  Saving current progress to files...")
                for category_key, deals_list in all_deals.items():
                    save_to_json(deals_list, f"{JSON_OUTPUT_FOLDER}/{category_key}.json")
        else:
            for store, img_file_list in image_files_dict.items():
                full_image_paths = list()
                for imgfile in img_file_list:
                    try:
                        parts = os.path.splitext(imgfile)[0].split('_')
                        store = parts[0]
                        acquired_date = parts[2]
                        page_number = int(parts[3])
                    except (IndexError, ValueError):
                        print(f"\nSkipping file with invalid name format: {imgfile} (Expected: 'store_YYYYMMDD.jpg')")
                        continue

                    image_path = os.path.join(IMAGE_INPUT_FOLDER, imgfile)

                    full_image_paths.list(image_path)

                    for full_imgpath in full_image_paths:
                        if model.is_exhausted:
                            if model.id == 'pro':
                                print(f'{model.name} er oppbrukt. Bytter til Gemini Flash.')
                                model = Gem_flash
                            elif model.id == 'flash':
                                print('Alle modeller er oppbrukt. Ingen flere bilder kan analyseres.')
                        


                        time_prev = time.perf_counter()
                        categorized_deals = analyze_flyer_image(full_imgpath, model)
                        time_new = time.perf_counter()
                        analysis_time = time_new - time_prev

                        if analysis_time < model.sleeptime:
                            time.sleep(model.sleeptime - analysis_time)
                            print(f'API is analyzing too quickly. Have to sleep for {model.sleeptime - analysis_time :.3f}s')

                        if categorized_deals:
                            for category_key, deals_list in categorized_deals.items():
                                if category_key in all_deals:
                                    for deal in deals_list:
                                        deal['store'] = store
                                        deal['acquired_date'] = acquired_date
                                        deal['page_number'] = page_number
                                        deal['AI_model_used'] = model.id
                                        all_deals[category_key].append(deal)
                            print("  Saving current progress to files...")
                            for category_key, deals_list in all_deals.items():
                                save_to_json(deals_list, f"{JSON_OUTPUT_FOLDER}/{category_key}.json")

                print("\nProcessing complete.")


    process_all_flyers()