from urllib.request import urlopen
import re
from datetime import datetime
import datetime
import time
import sys
import requests
import json
import os
from bs4 import BeautifulSoup
from pydantic_models import chosen_urls
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from google.genai import types
from google import genai
from google.genai import errors
from AI_model_setup import front_page_model
import traceback

def download_from_url(url,save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Image downloaded successfully to: {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")


def fetch_kundeavis(BUTIKKER, dato):
    '''Henter urler til alle kundeavis-sider i kupp.vg, og returnerer en dict med butikker som key og liste med urler som value.
    
    Dersom refresh_aviser == True vil programmet forsøke å laste ned ny html-kode fra kupp.vg.no.
    '''

    curr_date, år, uke = dato

    htmlDirectory = f"temp_output/kupphtml_{år}_{uke}.txt"

    downloaded_shops = []

    try:
        for entry in os.listdir(f'temp_output/bilder'):
            shopName = entry.split('_')[0]
            if shopName not in downloaded_shops:
                downloaded_shops.append(shopName)
        
        unique_stores = list(set(BUTIKKER).difference(set(downloaded_shops)))
        if not unique_stores:
            print('Kundeavisene til valgte butikker er allerede lasted ned')
            return None
        else:
            BUTIKKER = unique_stores
    except:
        pass


    url = "https://kupp.vg.no/"

    page = urlopen(url)

    html_bytes = page.read()
    html = html_bytes.decode("utf-8")

    with open(htmlDirectory, 'w', encoding='utf-8') as fil:
        fil.write(html)
        print('file written successfully!')
        
    
    kundeavisen = {}
    kundeavisen['header'] = [år, uke, BUTIKKER]

    for butikk in BUTIKKER:

        avis_src = f"https://s.kupp.no/prod/pages/{butikk}/{år}/{uke:02d}/"

        word = avis_src
        occurrences = []

        # Using re.finditer to get match objects with start and end indices
        for match in re.finditer(word, html):
            occurrences.append((match.start(), match.end()))
        src_occurrences = []


        extr_str_len = len('b372bf52-db70-44a0-8e4b-215d2fb74d9f.t')

        #TODO: BRUK HELLER if '.jpg' in str
        for occ_idx_strt, occ_idx_end in occurrences:
            occr_str = html[occ_idx_strt:occ_idx_end+extr_str_len]
            if '.t' in occr_str:
                continue
            for src_str in range(occ_idx_end, occ_idx_end+80):
                if html[src_str] == '.':
                    tmp_start, tmp_end = ((occ_idx_strt, src_str+4))
                    src_occurrences.append(html[tmp_start:tmp_end])


        kundeavisen[butikk] = src_occurrences

    return kundeavisen

def fetch_etilbudsavis(BUTIKKER, dato):

   # HELGETILBUDAVISER = {'Bunnpris':'bunnpris', 'REMA-1000':'rema-1000', 'Coop-Mega':'coop-mega', 'Coop-Prix':'coop-prix', 'Extra':'extra', 'KIWI':'kiwi', 'MENY':'meny', 'Obs':'obs', 'Joker':'joker', 'SPAR':'spar'}
    HELGETILBUDAVISER = {'bunnpris':'Bunnpris', 'rema-1000':'REMA-1000', 'coop-mega':'Coop-Mega', 'coop-prix':'Coop-Prix', 'extra':'Extra', 'kiwi':'KIWI', 'meny':'MENY', 'obs':'Obs', 'joker':'Joker', 'spar':'SPAR', 'coop-marked': 'coop marked'}


    curr_date, år, uke = dato
    kundeavisen = {}
    kundeavisen['header'] = [år, uke, list(BUTIKKER)]
    failed_stores = []
    page_struct = []
    API_KEY = os.environ["GEMINI_API_KEY"]

    service = Service(executable_path="/usr/bin/chromedriver")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")                # Required: Bypasses OS security model inside Docker
    options.add_argument("--disable-dev-shm-usage")     # Required: Prevents Docker from running out of memory
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"

    for helgetilbud in BUTIKKER:
        count = 0
        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.get("https://etilbudsavis.no")

            driver.add_cookie({
                'name': 'eta-location',
                'value': r'%7B%22latitude%22%3A63.4306%2C%22longitude%22%3A10.4037%2C%22geohash%22%3A%22u5r2uep%22%2C%22city%22%3A%22Trondheim%22%2C%22country%22%3A%22NO%22%2C%22mode%22%3A%22fallback%22%7D',
                'domain': '.etilbudsavis.no', 
                'path': '/',
            })

            url = f"https://www.etilbudsavis.no/{HELGETILBUDAVISER[helgetilbud]}" 
            driver.get(url)
            time.sleep(3)


            html_source = driver.page_source
            soup = BeautifulSoup(html_source, 'html.parser')
            all_publication_urls = []
            script_tag = soup.find("script", type="application/ld+json")


            if script_tag:
                json_data = json.loads(script_tag.string)
                graph = json_data.get("@graph", [])

                item_list = next((obj for obj in graph if obj.get("@type") == "ItemList"), None)
                publications = item_list.get("itemListElement", [])
                for pub in publications:
                    item = pub.get("item", {})
                    name = item.get("name")
                    url = item.get("url")


                    all_publication_urls.append(url)
            
            else:
                print(f'ERROR: No valid publication URLs for {helgetilbud}. Skipping.')
                failed_stores.append(helgetilbud)
                continue

            for pub_url in all_publication_urls:
                driver.get(pub_url)
                time.sleep(2)
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                page_divs = soup.find_all('div', attrs={"data-page-number": True})
                try:
                    front_page = page_divs[0].find('img')
                    if front_page and front_page.get("data-src-lg"):
                        save_path = f"temp_output/front_pages/{helgetilbud}_{count}.jpg"
                        download_from_url(front_page.get("data-src-lg"), save_path)
                        count += 1
                        

                        pub_url_element = {
                            "store": helgetilbud,
                            "URL": pub_url,
                            "front_page_path": save_path,
                            "divs": page_divs
                        }

                        page_struct.append(pub_url_element)
                    else:
                        raise ValueError("No valid page.")
                except Exception as e:
                    print(f'No valid front page. Skipping URL {pub_url} from store {helgetilbud}.')
                    continue

                    


        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()
            failed_stores.append(helgetilbud)
        
        else:
            print(f"Successfully extracted all valid publication URLs from {HELGETILBUDAVISER[helgetilbud]}")

        finally:
            driver.quit()


    contents = []
    prompt_final = """You are a grocery flyer analyzer. You are provided with the URL and front page of multiple publications for several different stores.
    Your goal is to correctly identify which URL for each store which corresponds to that weeks 'kundeavis', which is a flyer of all sales on food items for that store that week.
    """


    for i, item in enumerate(page_struct, start=1):
        prompt_final += f'--- Item {i} ---\nStore: {item["store"]}\nURL: {item["URL"]}\nImage is provided below.\n\n'
        
        contents.append(Image.open(item["front_page_path"]))

    final_contents = [prompt_final] + contents

    attempts = 0
    max_retries = 3

    while (attempts < max_retries+1):
        try:
            with genai.Client(api_key=API_KEY) as client:
                response = client.models.generate_content(
                model=front_page_model.id,
                contents=final_contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=chosen_urls,
                )
                )

            for pub_url_dict in json.loads(response.text)['results']:
                full_pub_url_dict = dict()
                for match_case in page_struct:
                    if pub_url_dict['URL'] == match_case['URL']:
                        full_pub_url_dict = match_case

                flyer_img_links = []
                for div in full_pub_url_dict['divs']:
                    img_tag = div.find('img')
                    if img_tag and img_tag.get("data-src-lg"):
                        flyer_img_links.append(img_tag.get("data-src-lg"))
                kundeavisen[pub_url_dict['store']] = flyer_img_links

            if failed_stores:
                print(f'Failed stores: {failed_stores}')
            else:
                print("All stores extracted successfully!")
            return kundeavisen
        except errors.APIError as e:
            if e.code == 429:   
                front_page_model.is_exhausted = True
                print(f"Error 429 recieved for front page analyzing. Aborting program.")
                return None
            elif e.code == 503:
                print("Error for high demand recieved. Will wait for 30 seconds before attempting again.")
                time.sleep(30)
                attempt += 1
            else: 
                print(f"General API request failure (attempt {attempt + 1}/{max_retries}): {e}")
                attempt += 1
    
    print("Max number of retries reached. Exiting program")
    sys.exit()

def download_kundeaviser(dato, kundeaviser_urls):

    current_date, år, uke = dato

    print('Header for valgt kundeavis: ' , kundeaviser_urls['header'])

    try:
        os.mkdir(f'temp_output/bilder')
    except:
        pass


    for key, value in kundeaviser_urls.items():
        if key == 'header':
            continue
        image_urls = value
        butikk = key
        for idx, url in enumerate(image_urls):
            save_location = f"temp_output/bilder/{butikk}_{år}_{uke}_{idx+1}.jpg" 
            download_from_url(url, save_location)



if __name__ == '__main__':
    current_date = datetime.datetime.now()
    år = current_date.year
    uke = current_date.date().isocalendar()[1]
    dato = [current_date, år, uke]
    BUTIKKER = ['bunnpris', 'coop-mega']

    URLs = fetch_etilbudsavis(BUTIKKER, dato)
    download_kundeaviser(dato, URLs)