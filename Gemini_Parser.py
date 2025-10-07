import os
import json
import base64
import time
import datetime
from datetime import datetime
import requests
import sys
from bs4 import BeautifulSoup



def Gemini_parser(BUTIKKER, DATO, write_mode = 'add'):
    '''Sender API-calls til Gemini Flash 2.5 for å ekstrahere matvarer fra kundeavisene
    
    Har to "moduser" for å lagre data ved:

    "add" - LEGGER TIL ny data som leses fra kundeaviser på eksisterende JSON-filer 
    "replace" - SLETTER eksisterende JSON-filer og skaper nye med data som leses fra kundeaviser (standard)

    '''

    current_date, år, UKE = DATO


#    if write_mode == 'add':
#        overwrite = False
#    elif write_mode == 'replace':
#        overwrite = True
#    else:
#        raise ValueError("Ikke godkjent write_mode")
    overwrite = True


    # --- CONFIGURATION ---
    # IMPORTANT: Get your API key from Google AI Studio and paste it here.
    # https://aistudio.google.com/app/apikey
    API_KEY = os.getenv("GEMINI_API_KEY")

    if not API_KEY:
        sys.exit("❌ ERROR: API_KEY not found in environment variables!")
    else:
        print("✅ API_KEY is present (value hidden).")

    # Folder where your flyer images are stored (e.g., 'rema1000_20250809.jpg')
    IMAGE_INPUT_FOLDER = f"temp_output/bilder" 
    JSON_OUTPUT_FOLDER = "temp_output/results_JSON"


    # --- SCRIPT ---

    def analyze_flyer_image(image_path):
        """
        Analyzes a single flyer image using the Gemini API and returns structured data.
        """
        print(f"Processing image: {image_path}...")

        # 1. Encode the image to base64
        try:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
        except IOError as e:
            print(f"  Error reading file: {e}")
            return None

        # 2. Construct the prompt for the Gemini API
        # This is a highly detailed prompt to ensure the model returns data in the precise format needed.
        prompt = """
        Analyze the provided image of a Norwegian grocery store flyer.
        Identify and categorize all distinct product offers into five specific types.
        Return the result as a single, valid JSON object with five keys. Each key should contain an array of objects for that category. If a category has no offers, its array must be empty.

        1.  `price_deals`: Standard price reductions.
            - `name`: The main name of the product.
            - `total_price`: The sale price as a decimal number.
            - `price_per_unit`: The price per kg or liter, as a decimal number, or null if not present.
            - `total_mass`: The total weight/volume as a decimal number (e.g., "500 g" becomes 0.5, "1.5 l" becomes 1.5), or null.
            - `unit`: The unit of measurement, either "kg" or "l". Infer from the product type (e.g., meat is kg, milk is l).

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

        # 3. Prepare the API request payload
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={API_KEY}"
        
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

        # 4. Make the API call with retries for robustness
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=90)
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

        if not overwrite:

            json_url = "https://askhf.folk.ntnu.no/temp_JSON/"


            response = requests.get(json_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all("a"):
                href = link.get("href")
                if href and href.endswith(".json"):
                    file_url = json_url + href
                    r = requests.get(file_url)
                    with open(f'{JSON_OUTPUT_FOLDER}\\{href}', "wb") as f:
                        f.write(r.content)
            with open(f'{JSON_OUTPUT_FOLDER}/kroner_off_deals.json', 'r', encoding='utf-8') as f:
                kroner_off_deals = json.load(f)
            with open(f'{JSON_OUTPUT_FOLDER}/{UKE}/multibuy_for_price_deals.json', 'r', encoding='utf-8') as f:
                multibuy_for_price_deals = json.load(f)
            with open(f'{JSON_OUTPUT_FOLDER}/{UKE}/percentage_deals.json', 'r', encoding='utf-8') as f:
                percentage_deals = json.load(f)
            with open(f'{JSON_OUTPUT_FOLDER}/{UKE}/price_deals.json', 'r', encoding='utf-8') as f:
                price_deals = json.load(f)
            with open(f'{JSON_OUTPUT_FOLDER}/{UKE}/three_for_two_deals.json', 'r', encoding='utf-8') as f:
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


        image_files = []
        for f in os.listdir(IMAGE_INPUT_FOLDER):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                for shop in BUTIKKER:
                    if shop in f:
                        image_files.append(f)
                        break


        #image_files = [f for f in os.listdir(IMAGE_INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        if not image_files:
            print(f"No image files found in '{IMAGE_INPUT_FOLDER}'.")
            return

        print(f"Found {len(image_files)} images to process.")

        for i, filename in enumerate(image_files):
            try:
                parts = os.path.splitext(filename)[0].split('_')
                store = parts[0]
                acquired_date = parts[2]
                page_number = int(parts[3]) + 1
            except (IndexError, ValueError):
                print(f"\nSkipping file with invalid name format: {filename} (Expected: 'store_YYYYMMDD.jpg')")
                continue

            image_path = os.path.join(IMAGE_INPUT_FOLDER, filename)
            categorized_deals = analyze_flyer_image(image_path)

            if categorized_deals:
                # Iterate through the categories and append data to the master lists
                for category_key, deals_list in categorized_deals.items():
                    if category_key in all_deals:
                        for deal in deals_list:
                            deal['store'] = store
                            deal['acquired_date'] = acquired_date
                            deal['page_number'] = page_number
                            all_deals[category_key].append(deal)
                print("  Saving current progress to files...")
                for category_key, deals_list in all_deals.items():
                    save_to_json(deals_list, f"{JSON_OUTPUT_FOLDER}/{category_key}.json")
            
            if i < len(image_files) - 1:
                print("  Waiting 2 seconds before next request...")
                time.sleep(2)

        print("\nProcessing complete.")

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



    process_all_flyers()
