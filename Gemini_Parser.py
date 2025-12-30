import os
import json
import base64
import time
import requests
import sys
from bs4 import BeautifulSoup
import numpy as np
import math


def Gemini_parser(BUTIKKER, DATO, add_tmp_json=False, batchsize=None, prev_failed_batches=None):
    '''Sender API-calls for å ekstrahere matvarer fra kundeavisene'''

    current_date, år, UKE = DATO
    API_KEY = os.getenv("GEMINI_API_KEY")


    max_retries = 3
    max_timeout = 190

    RPD_tol = 0.8 #Tall mellom 0 og 1, angir (1- andel) av RPD-1 som går til "redundancy", og angir dermed også batchsize
    failed_batches = dict()
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

    with open('prompts.json', 'r', encoding='utf-8') as f:
        prompts = json.load(f)
        prompt = prompts['batch'] if batchsize > 1 else prompts['non_batch']


    class API_model():

        def __init__(self, id, name, RPM, RPD):
            self.id = id
            self.name = name
            self.n_calls = 0
            self.is_exhausted = False
            self.RPM = RPM
            self.sleeptime = 60 // self.RPM
            self.rate_limit = RPD
            self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.id}:generateContent?key={API_KEY}"

        def rate_limit_reached(self):
            if self.n_calls > self.rate_limit:
                self.is_exhausted = True
                return True
            else:
                return False


    Gem_flash = API_model('gemini-2.5-flash', 'Gemini Flash', 5, 20)
    Gem3_flash = API_model('gemini-3-flash', 'Gemini 3 Flash', 5, 20)
    #Gem_pro = API_model('pro', 'Gemini Pro', 2, 50)

    AI_models = [Gem3_flash, Gem_flash]

    
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

    def analyze_flyer_batch(flyer_batch, model, batchidx = None, n_batches=None):
        image_parts = []
        batch_n = batchidx+1
    
        # Går igjennom hver flyer-objekt i listen og legger til bildedata
        for flyer_page in flyer_batch:
            try:
                with open(flyer_page.img_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    image_parts.append({
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": image_data
                        }
                    })
            except IOError as e:
                print(f"Skipping file due to error: {flyer_page.img_path} - {e}")
                continue

        if not image_parts:
            print("No valid images to process.")
            return None

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}] + image_parts 
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                # Hvis bilder blir for høy-def, øk antall tokens med kode under
                # "maxOutputTokens": 8192 
            }
        }

        headers = {'Content-Type': 'application/json'}

        errorFlag = False
        attempt = 0
        err_counter = 0
        while attempt < (max_retries):

            model.n_calls += 1

            try:
                response = requests.post(model.api_url, headers=headers, json=payload, timeout=max_timeout)
                response.raise_for_status()
                
                extracted_data = response.json()
                
                json_text = extracted_data['candidates'][0]['content']['parts'][0]['text']
                categorized_deals = json.loads(json_text)
                if batchsize <=1:
                    if all(k in flyer_content['deals'] for k in required_keys):
                        flyer_batch[0].categorized_deal = flyer_content['deals']
                        flyer_batch[0].AI_model_used = model.id
                        return flyer_content['deals']

                for flyer_content in categorized_deals:
                    i = flyer_content['image_index']
                    flyer_batch[i].AI_model_used = model.id
                    if all(k in flyer_content['deals'] for k in required_keys):
                        flyer_batch[i].categorized_deal = flyer_content['deals']
                    else:
                        print(f'Ugyldig struktur på følgende bilde: {flyer_batch[i].img_path}. Hoppes over.')
                        errorFlag = True
                print(f'\nDeals successfully extracted from batch nr. {batch_n} ({flyer_batch[0].store} | {flyer_batch[-1].store})')
                return None

            except requests.exceptions.RequestException as e:
                print(f"  API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                #Hvis APIen sender kode 429 ("Rate limit reached") så skal modellen byttes
                if e.response is not None and e.response.status_code == 429:
                    model.is_exhausted = True
                    print(f"Error 429 motatt. Slutter nå å bruke {model.name}.")
                    return None
                elif e.response.status_code == 503 and err_counter < 4:
                    attempt -= 1
                    err_counter +=1
                    print(f'Error 503. err_counter: {err_counter}')
                    time.sleep(5)

                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    print(f"  Final API request failed. Response: {response.text if 'response' in locals() else 'No response'}")
                    errorFlag = True
            except (KeyError, IndexError, json.JSONDecodeError, ValueError) as e:
                print(f"  Error parsing API response (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"  Received data: {response.text if 'response' in locals() else 'No response'}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    errorFlag = True
            
            attempt += 1
        if errorFlag:
            print(f'\n\n Batch nr {batch_n} av {n_batches} har ikke blitt behandlet. Går videre til neste batch.\n\n')
            failed_batches[(batchidx, n_batches)] = flyer_batch
            return None
        


        return None

    def process_all_flyers(batchsize=batchsize):
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
            
            def __repr__(self):
                return f"({self.store}-{self.page_number})"

            def create_dealsobj(self):
                processed_deals = {}
                if hasattr(self, 'categorized_deal'):
                    if self.categorized_deal:
                        for category_key, category_deals in self.categorized_deal.items():
                            processed_deals[category_key] = []
                            for deal in category_deals:
                                deal['name'] = deal['name'].capitalize()
                                deal['store'] = self.store
                                deal['acquired_date'] = self.acquired_date
                                deal['page_number'] = int(self.page_number)
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


        model = AI_models[0]


        if batchsize is None:
            batchsize = math.ceil(len(full_flyer_list)/(RPD_tol*model.rate_limit))


        if batchsize > 1:
            n_batches = math.ceil(len(full_flyer_list)/batchsize)
            batched_flyer_list = np.array_split(full_flyer_list, n_batches)
            for idx, flyer_batch in enumerate(batched_flyer_list):
                if prev_failed_batches and idx + 1 not in prev_failed_batches:
                    continue
                analyze_flyer_batch(flyer_batch, model, batchidx=idx, n_batches = n_batches)
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
                if model.is_exhausted:
                    model_idx = AI_models.index(model)
                    if model_idx == len(AI_models):
                        print('Alle AI-modeller brukt opp. Må stoppe prosessen her.')
                        remaining_batches = full_flyer_list[idx+1:]
                        failed_batches.extend(remaining_batches)
                        break
                    else:
                        model = AI_models[model_idx+1]



        else:
            for store, flyer_batch in batch_image_dict.items():
                print(f'Analyserer nå butikken: {store}')
                for flyer in flyer_batch:
                    analyze_flyer_batch([flyer], model)
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
                        if model.is_exhausted:
                            model_idx = AI_models.index(model)
                            if model_idx == len(AI_models):
                                print('Alle AI-modeller brukt opp. Må stoppe prosessen her.')
                                remaining_batches = full_flyer_list[idx+1:]
                        failed_batches.extend(remaining_batches)
                        break
                    else:
                        model = AI_models[model_idx+1]

        if failed_batches:
            final_nbatch_list = []
            print(f'ALLE MISLYKKEDE BATCHES: \n\n')
            for (idx, n_batches), batch in failed_batches.items():
                print(f'batch {idx+1}/{n_batches}: ', batch)
                final_nbatch_list.append(idx+1)
            print('Liste med alle failed batchnr (ikke idx): ', final_nbatch_list)
        print("\nProcessing complete.")


    process_all_flyers()