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
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal
from PIL import Image
from enum import Enum
import schemas


def Gemini_parser(BUTIKKER, add_website_json=False, add_tmp_json=False, batchsize=None, prev_failed_batches=None):
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


    class API_model():

        def __init__(self, id, name, RPM, RPD):
            self.id = id
            self.name = name
            self.n_calls = 0
            self.is_exhausted = False
            self.RPM = RPM
            self.sleeptime = 60 // self.RPM
            self.rate_limit = RPD

        def rate_limit_reached(self):
            if self.n_calls > self.rate_limit:
                self.is_exhausted = True
                return True
            else:
                return False


    Gem25_flash = API_model('gemini-2.5-flash', 'Gemini Flash', 5, 20)
    Gem3_flash = API_model('gemini-3-flash-preview', 'Gemini 3 Flash', 5, 20)
    Gem31_flash_lite = API_model('gemini-3.1-flash-lite-preview', 'Gemini 3.1 Flash Lite', 15, 500)
    #Gem_pro = API_model('pro', 'Gemini Pro', 2, 50)

    AI_models = [Gem3_flash, Gem31_flash_lite, Gem25_flash]

    
    def save_to_json(data : pd.DataFrame, filename):
        """Saves a list of data to a JSON file"""
        try:
            data.to_json(filename, force_ascii=False, orient='records', indent=4)
            print(f"Successfully saved {len(data)} items to '{filename}'.")
        except IOError as e:
            print(f"Error writing to output file '{filename}': {e}")

    def analyze_flyer_batch(flyer_batch, model : API_model, batchidx = None, n_batches=None):

        with genai.Client(api_key = API_KEY) as client:
            batch_image_list = list()
            batch_n = batchidx+1
        
            # Går igjennom hver flyer-objekt i listen og legger til bildedata
            for flyer_page in flyer_batch:
                try:
                    #"Image index" refererer egentlig til sidetall i kundeavisen, men denne formuleringen er bedre for LLM-forståelse
                    batch_image_list.append(f"Image index {flyer_page.page_number}, Store {flyer_page.store}:")
                    batch_image_list.append(Image.open(flyer_page.img_path))
                except IOError as e:
                    print(f"Skipping file due to error: {flyer_page.img_path} - {e}")
                    continue

            if not batch_image_list:
                print("No valid images to process.")
                return None


            errorFlag = False
            attempt = 0
            while attempt < (max_retries):

                model.n_calls += 1

                try:
                    response = client.models.generate_content(
                    model=model.id,
                    contents=[prompt,batch_image_list],
                    config={'response_mime_type':"application/json",
                            "response_schema": schemas.flyer_batch.model_json_schema()}
                    )
                    
                    #LLM formaterer alle deals inn i en key "flyers", så må hente faktisk respons fra den keyen her
                    batch_deal_df = pd.DataFrame(json.loads(response.text)['flyers'])
                    if not batch_deal_df.empty:
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
                        else: 
                            print(f"  API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                            attempt += 1
                except Exception as e:
                    print(f"  API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                    attempt += 1



                if attempt < max_retries - 1:
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