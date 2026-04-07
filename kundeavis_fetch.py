from urllib.request import urlopen
import re
from datetime import datetime
import datetime
import time
import requests
import json
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


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

def fetch_helgetilbud(dato):

    HELGETILBUDAVISER = {'bunnpris-no':'bunnpris', 'coop-prix-no':'coop-prix'}

    #['rema-1000', 'kiwi', 'extra','bunnpris','meny','coop-prix','joker','spar','coop-mega','coop-marked','obs']
    curr_date, år, uke = dato
    kundeavisen = {}
    kundeavisen['header'] = [år, uke, list(HELGETILBUDAVISER.values())]

    chromedriver_path = 'chromedriver.exe' 
    service = Service(chromedriver_path)
    options = Options()
    options.add_argument("--headless")


    for idx, helgetilbud in enumerate(HELGETILBUDAVISER.keys()):
        try:
            driver = webdriver.Chrome(service=service, options=options)
            url = f"https://mattilbud.no/kundeaviser/{helgetilbud}" 
            driver.get(url)

            time.sleep(0.3) 

            html_source = driver.page_source
            href_links = list()
            matches = re.finditer('href="/kundeaviser', html_source)
            for match in matches:
                href_links.append(html_source[match.start():match.end() + 50].split('"')[1])

            finalurl = "https://mattilbud.no" + href_links[1]
        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            driver.quit()


        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(finalurl)
            time.sleep(0.3) 

            page = driver.page_source
            soup = BeautifulSoup(page, features="html.parser")

            matches = soup.find_all('img', alt=True)

            image_urls = list()

            for url in matches:
                image_urls.append(url['src'])
        except Exception as e:
            print(f'En feil har skjedd: {e}')
        
        finally:
            driver.quit()

        kundeavisen[list(HELGETILBUDAVISER.values())[idx]] = image_urls

    return kundeavisen

def fetch_kundeavis_mattilbud(dato):

    HELGETILBUDAVISER = {'bunnpris-no':'bunnpris', 'coop-prix-no':'coop-prix'}

    #['rema-1000', 'kiwi', 'extra','bunnpris','meny','coop-prix','joker','spar','coop-mega','coop-marked','obs']
    curr_date, år, uke = dato
    kundeavisen = {}
    kundeavisen['header'] = [år, uke, list(HELGETILBUDAVISER.values())]

    chromedriver_path = 'chromedriver.exe' 
    service = Service(chromedriver_path)
    options = Options()
    options.add_argument("--headless")


    for idx, helgetilbud in enumerate(HELGETILBUDAVISER.keys()):
        try:
            driver = webdriver.Chrome(service=service, options=options)
            url = f"https://mattilbud.no/kundeaviser/{helgetilbud}" 
            driver.get(url)

            time.sleep(0.3) 

            html_source = driver.page_source
            href_links = list()
            matches = re.finditer('href="/kundeaviser', html_source)
            for match in matches:
                href_links.append(html_source[match.start():match.end() + 50].split('"')[1])

            finalurl = "https://mattilbud.no" + href_links[1]
        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            driver.quit()


        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(finalurl)
            time.sleep(0.3) 

            page = driver.page_source
            soup = BeautifulSoup(page, features="html.parser")

            matches = soup.find_all('img', alt=True)

            image_urls = list()

            for url in matches:
                image_urls.append(url['src'])
        except Exception as e:
            print(f'En feil har skjedd: {e}')
        
        finally:
            driver.quit()

        kundeavisen[list(HELGETILBUDAVISER.values())[idx]] = image_urls

    return kundeavisen


def fetch_etilbudsavis(BUTIKKER, dato):

   # HELGETILBUDAVISER = {'Bunnpris':'bunnpris', 'REMA-1000':'rema-1000', 'Coop-Mega':'coop-mega', 'Coop-Prix':'coop-prix', 'Extra':'extra', 'KIWI':'kiwi', 'MENY':'meny', 'Obs':'obs', 'Joker':'joker', 'SPAR':'spar'}
    HELGETILBUDAVISER = {'bunnpris':'Bunnpris', 'rema-1000':'REMA-1000', 'coop-mega':'Coop-Mega', 'coop-prix':'Coop-Prix', 'extra':'Extra', 'kiwi':'KIWI', 'meny':'MENY', 'obs':'Obs', 'joker':'Joker', 'spar':'SPAR', 'coop-marked': 'coop marked'}


    curr_date, år, uke = dato
    kundeavisen = {}
    kundeavisen['header'] = [år, uke, list(BUTIKKER)]
    failed_stores = []

    service = Service(ChromeDriverManager().install())
    options = Options()
    options.add_argument("--headless")


    for helgetilbud in BUTIKKER:
        try:
            driver = webdriver.Chrome(service=service, options=options)
            url = f"https://www.etilbudsavis.no/{HELGETILBUDAVISER[helgetilbud]}" 
            driver.get(url)
            time.sleep(3)


            html_source = driver.page_source
            soup = BeautifulSoup(html_source, 'html.parser')
            all_publication_urls = []
            final_img_links = []
            label_keywords = ["uke", "kundeavis", "coop mega", "obs", 'coop marked']

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

                    if any(word in name.lower() for word in label_keywords):
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
                final_img_links = []

                #Finner bildene i divsa. bruker spesifikt data-src-lg (large) fordi best kvalitet på bilder.
                for div in page_divs:
                    img_tag = div.find('img')
                    if img_tag and img_tag.get("data-src-lg"):
                        final_img_links.append(img_tag.get("data-src-lg"))

        except Exception as e:
            print(f"An error occurred: {e}")
            failed_stores.append(helgetilbud)
        
        else:
            kundeavisen[HELGETILBUDAVISER[helgetilbud]] = final_img_links
            print(f"Successfully extracted kundeavis from {HELGETILBUDAVISER[helgetilbud]}")

        finally:
            driver.quit()

    if failed_stores:
        print(f'Failed stores: {failed_stores}')
    else:
        print("All stores extracted successfully!")
    return kundeavisen

def download_kundeaviser(dato, kundeaviser_urls):

    current_date, år, uke = dato

    print('Header for valgt kundeavis: ' , kundeaviser_urls['header'])

    try:
        os.mkdir(f'temp_output/bilder')
    except:
        pass

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

    URLs = fetch_etilbudsavis(dato)