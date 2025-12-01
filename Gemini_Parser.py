import os
import json
import base64
import time
import datetime
from datetime import datetime
import requests
import sys
from bs4 import BeautifulSoup



def Gemini_parser(BUTIKKER, DATO, add_tmp_json=False):
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
            self.RPM = ModelData['RPM']
            self.sleeptime = 60 // self.RPM
            self.rate_limit = ModelData['rateLimit']
            self.api_url = ModelData['api_url']

        def rate_limit_reached(self):
            if self.n_calls > self.rate_limit:
                return True
            else:
                return False

    flash_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    pro_api_url =   f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={API_KEY}'

    API_model_data = {
        'flash': {'name': 'Gemini Pro', 'RPM': 10, 'rateLimit': 250, 'api_url':flash_api_url},
        'pro':   {'name': 'Gemini Flash', 'RPM': 2,  'rateLimit': 50,  'api_url':pro_api_url}
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
                if e.response is not None and e.request.status_code == 429:
                    model.r_calls = model.rate_limit
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
        image_files = []
        for f in os.listdir(IMAGE_INPUT_FOLDER):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                for shop in BUTIKKER:
                    if shop in f:
                        if shop in image_files_dict:
                            image_files_dict[shop].append(f)
                        else:
                            image_files_dict[shop] = [f]
                        image_files.append(f)
                        break


        #image_files = [f for f in os.listdir(IMAGE_INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        if not image_files:
            print(f"No image files found in '{IMAGE_INPUT_FOLDER}'.")
            return
        

        print(f"{len(image_files)} bilder skal behandles.")


        time_prev = time.perf_counter()
        for store, img_file_list in image_files_dict.items():
            for imgfile in img_file_list:
                try:
                    parts = os.path.splitext(imgfile)[0].split('_')
                    store = parts[0]
                    acquired_date = parts[2]
                    page_number = int(parts[3]) + 1
                except (IndexError, ValueError):
                    print(f"\nSkipping file with invalid name format: {imgfile} (Expected: 'store_YYYYMMDD.jpg')")
                    continue

                image_path = os.path.join(IMAGE_INPUT_FOLDER, imgfile)

                if not Gem_pro.rate_limit_reached():
                    model = Gem_pro
                else:
                    model = Gem_flash

                
                categorized_deals = analyze_flyer_image(image_path, model)
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