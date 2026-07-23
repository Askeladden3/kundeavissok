import os
import json
import time
import requests
import sys
from bs4 import BeautifulSoup
import numpy as np
import math
import pandas as pd
from google import genai
from google.genai import errors
from PIL import Image
from pydantic_models import FlyerBatch
from openai import OpenAI


def encode_image_to_data_uri(image_path: str) -> str:
    """Reads an image file and returns a base64 data URI."""
    with open(image_path, "rb") as image_file:
        encoded_string = Image.open(image_path).convert("RGB").tobytes()
        b64 = base64.b64encode(encoded_string).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def model_api_call(
    provider: str,
    model_id: str,
    prompt: str,
    image_paths: list,
    response_format: type,
    temperature: float = 0.3,
    response_mime_type: str = "application/json"
):
    """Unified API call function for both Google and OpenAI providers.
    
    Args:
        provider: 'google' or 'openai'
        model_id: Model identifier (e.g. 'gemini-3.5-flash' or '/models/gemma4-12B-nvfp4')
        prompt: The text prompt
        image_paths: List of image file paths to include
        response_format: Pydantic model class for structured output
        temperature: Sampling temperature (default 0.3)
        response_mime_type: MIME type for response (default 'application/json')
    
    Returns:
        For Google: response.text (JSON string)
        For OpenAI: parsed Pydantic model instance
    """
    import base64

    # Initialize provider clients
    if provider == "google":
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    elif provider == "openai":
        # Use hardcoded local backend URL and dummy key (no auth needed for local)
        client = OpenAI(base_url="http://100.98.148.94:8001/v1", api_key="dummy-key")
    else:
        raise ValueError(f"Unknown provider: {provider}. Must be 'google' or 'openai'.")

    # Build message content list
    content = [{"type": "text", "text": prompt}]
    for img_path in image_paths:
        if provider == "openai":
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": encode_image_to_data_uri(img_path)},
                }
            )
        else:
            content.append(Image.open(img_path))

    if not content:
        raise ValueError("No content (prompt or images) provided.")

    try:
        if provider == "google":
            response = client.models.generate_content(
                model=model_id,
                contents=content,
                config={"response_mime_type": response_mime_type,
                        "response_schema": response_format.model_json_schema()}
            )
            return response.text
        else:  # openai
            response = client.beta.chat.completions.parse(
                model=model_id,
                messages=[{"role": "user", "content": content}],
                response_format=response_format,
                temperature=temperature,
            )
            return response.choices[0].message.parsed

    except Exception as e:
        raise RuntimeError(f"API call failed for provider '{provider}' with model '{model_id}': {e}")


def Gemini_parser(BUTIKKER, AI_models, add_website_json=False, add_tmp_json=False, batchsize=None, prev_failed_batches=None):
    '''Sends API calls to extract food items from grocery flyers'''

    all_deals = ['standard_deal', 'percentage_deal', 'bogo_deal']

    API_KEY = os.environ["GEMINI_API_KEY"]


    max_retries = 3

    RPD_tol = 0.8 #Tall mellom 0 og 1, angir (1- andel) av RPD-1 som går til "redundancy", og angir dermed også batchsize
    failed_batches = dict()

    if not API_KEY:
        sys.exit("ERROR: API_KEY not found in environment variables!")
    else:
        print("API_KEY is present (value hidden).")

    IMAGE_INPUT_FOLDER = f"temp_output/bilder" 
    JSON_OUTPUT_FOLDER = "temp_output/results_JSON"

    try:
        os.mkdir(JSON_OUTPUT_FOLDER)
    except:
        pass

    with open('prompts.txt', 'r', encoding='utf-8') as f:
        prompts = f.read()
        prompts = prompts.split('/'*5)
        prompt = prompts[1]
    
    def save_to_json(data : pd.DataFrame, filename):
        """Saves a list of data to a JSON file"""
        try:
            data.to_json(filename, force_ascii=False, orient='records', indent=4)
            print(f"Successfully saved {len(data)} items to '{filename}'.")
        except IOError as e:
            print(f"Error writing to output file '{filename}': {e}")

    def analyze_flyer_batch(flyer_batch, model, batchidx = None, n_batches=None):

        batch_image_list = list()
        batch_image_paths = list()
        batch_n = batchidx+1
        
        # Build image list for both providers
        for flyer_page in flyer_batch:
            try:
                batch_image_list.append(f"Image index {flyer_page.page_number}, Store {flyer_page.store}:")
                img_path = flyer_page.img_path
                batch_image_paths.append(img_path)
                batch_image_list.append(Image.open(img_path))
            except IOError as e:
                print(f"Skipping file due to error: {img_path} - {e}")
                continue

        if not batch_image_paths:
            print("No valid images to process.")
            return None

        model_id = model.id  # Ensure we use the model's id field
        # Detect provider: OpenAI if model_id starts with '/models/', else Google
        provider = "openai" if model_id.startswith("/models/") else "google"

        errorFlag = False
        attempt = 0
        while attempt < (max_retries):
            model.n_calls += 1

            try:
                response = model_api_call(
                    provider=provider,
                    model_id=model_id,
                    prompt=prompt,
                    image_paths=batch_image_paths,
                    response_format=FlyerBatch,
                    temperature=0.3,
                    response_mime_type="application/json"
                )
                
                # Handle different response formats
                batch_deal_df = pd.DataFrame([])
                if provider == "google":
                    # Google returns a JSON string
                    try:
                        batch_deal_df = pd.DataFrame(json.loads(response)['flyers'])
                    except (KeyError, TypeError) as e:
                        print(f"  Failed to parse Google response: {e}")
                        print(f"  Response content: {response[:200]}")
                        raise
                else:  # openai
                    # OpenAI returns a parsed Pydantic model
                    batch_deal_df = pd.DataFrame([response])
                    batch_deal_df = batch_deal_df.rename(columns={"image_index":"page_number"})
                    try:
                        batch_deal_df.loc[batch_deal_df['category'] == 'eggs', 'unit'] = 'stk'
                    except:
                        pass

                print(f'\nDeals successfully extracted from batch nr. {batch_n} ({flyer_batch[0].store} | {flyer_batch[-1].store})')
                return batch_deal_df

            except errors.APIError as e:
                if e.code == 429:   
                    model.is_exhausted = True
                    print(f"Error 429 recieved. Now stopping the use of {model.name}.")
                    return None
                elif e.code == 503:
                    print("Error for high demand recieved. WIll now wait 25 extra seconds between each try.")
                    model.in_high_demand = True
                    attempt += 1
                else: 
                    print(f"  API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                    attempt += 1
            except RuntimeError as e:
                # This catches invalid model IDs and other provider errors
                print(f"  API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                attempt += 1
            except Exception as e:
                print(f"  API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                attempt += 1

            if attempt < max_retries - 1:
                if model.in_high_demand:
                    time.sleep(25)
                time.sleep(5)
            else:
                print(f"  Final API request failed. Response: {response.text if 'response' in locals() else 'No response'}")
                errorFlag = True
                    
                attempt += 1
            if errorFlag:
                print(f'\n\n Batch nr {batch_n} of {n_batches} has not been processed. Moving on to next batch.\n\n')
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
            '''

            def __init__(self, prop):
                self.store = prop['store']
                self.page_number = prop['page_number']
                self.img_path = prop['img_path']
            
            def __repr__(self):
                return f"({self.store}-{self.page_number})"
        
        def is_dir_empty(path):
            with os.scandir(path) as it:
                return not any(it)

        ALL_DEALS_DF = None
        if add_website_json:

            if not is_dir_empty(JSON_OUTPUT_FOLDER):
                print("Cannot add website JSON to json_output_folder as there are already files there")
                sys.exit()

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


        
        if add_tmp_json or add_website_json:
            if not os.path.exists(JSON_OUTPUT_FOLDER):
                print("Program is set to append json already present in JSON folder, but folder doesnt exist")
                sys.exit()
            elif is_dir_empty(JSON_OUTPUT_FOLDER):
                print("Program is set to add json already present in JSON folder, but folder has no files!")
                sys.exit()

            tmp_df_list = []
            for category in all_deals:
                data = pd.read_json(f'{JSON_OUTPUT_FOLDER}/{category}.json', encoding='utf-8')
                data['deal_type'] = category
                tmp_df_list.append(data)

            ALL_DEALS_DF = pd.concat(tmp_df_list, ignore_index=True)
            print(f"Number of items before start of parsing is {len(ALL_DEALS_DF)}. Does it seem correct? \n\n")
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
        n_images = 0
        for f in os.listdir(IMAGE_INPUT_FOLDER):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                for shop in BUTIKKER:
                    if shop in f:
                        prop = {
                            'store': shop,
                            'page_number': f.split('_')[-1].split('.')[0],
                            'img_path': os.path.join(IMAGE_INPUT_FOLDER, f)
                            }
                        
                        curr_flyer = flyer(prop)
                        if shop in batch_image_dict:
                            batch_image_dict[shop].append(curr_flyer)
                        else:
                            batch_image_dict[shop] = [curr_flyer]
                        full_flyer_list.append(curr_flyer)
                        n_images += 1
                        break

        if not batch_image_dict:
            print(f"No image files found in '{IMAGE_INPUT_FOLDER}'.")
            return
        

        print(f"{n_images} bilder skal behandles.")


        model = AI_models[0]


        if batchsize is None:
            batchsize = math.ceil(len(full_flyer_list)/(RPD_tol*model.rate_limit))


        n_batches = math.ceil(len(full_flyer_list)/batchsize)
        print(f'Number of batches to be processed: {n_batches}\n')
        batched_flyer_list = np.array_split(full_flyer_list, n_batches)
        for idx, flyer_batch in enumerate(batched_flyer_list):
            if prev_failed_batches and idx + 1 not in prev_failed_batches:
                continue
            deals_df = analyze_flyer_batch(flyer_batch, model, batchidx=idx, n_batches = n_batches)
            if model.is_exhausted:
                model_idx = AI_models.index(model)
                if model_idx == len(AI_models)-1:
                    print('Alle AI-modeller brukt opp. Må stoppe prosessen her.')
                    remaining_batches = full_flyer_list[idx+1:]
                    failed_batches.extend(remaining_batches)
                    break
                else:
                    model = AI_models[model_idx+1]
                    print(f"Switched to model: {model.name}")
                    deals_df = analyze_flyer_batch(flyer_batch, model, batchidx=idx, n_batches = n_batches)

            if deals_df is None:
                deals_df = pd.DataFrame([])
            if not deals_df.empty:
                deals_df['AI_model_used'] = model.id
            if ALL_DEALS_DF is None:
                ALL_DEALS_DF = deals_df
            else:
                ALL_DEALS_DF = pd.concat([ALL_DEALS_DF, deals_df], ignore_index=True)
            grouped_dfs = {key : group for key, group in ALL_DEALS_DF.groupby('deal_type')}
            print("  Saving current progress to files...")
            for category_key, df in grouped_dfs.items():
                #Fjerner duplikatvarer fra samme butikk
                df['name_lowercase'] = df['name'].str.lower()
                df.drop_duplicates(subset=['store', 'name_lowercase'], keep='first', ignore_index=True, inplace = True)
                df.drop(columns=['name_lowercase'], inplace=True)

                where_gram = df['unit'] == 'g'
                where_ml = df['unit'] == 'ml'
                df.loc[where_gram, 'total_mass'] = df.loc[where_gram, 'total_mass'].apply(lambda x: x/1000)
                df.loc[where_ml, 'total_mass'] = df.loc[where_ml, 'total_mass'].apply(lambda x: x/1000)
                df.loc[where_gram, 'unit'] = 'kg'
                df.loc[where_ml, 'unit'] = 'L'

                save_to_json(df.dropna(axis=1, how='all'), f"{JSON_OUTPUT_FOLDER}/{category_key}.json")



        if failed_batches:
            final_nbatch_list = []
            print(f'ALLE MISLYKKEDE BATCHES: \n\n')
            for (idx, n_batches), batch in failed_batches.items():
                print(f'batch {idx+1}/{n_batches}: ', batch)
                final_nbatch_list.append(idx+1)
            print('Liste med alle failed batchnr (ikke idx): ', final_nbatch_list)
        print("\nProcessing complete.")


    process_all_flyers()