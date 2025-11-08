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
from selenium.webdriver.common.by import By


def fetch_kundeavis(BUTIKKER, dato, refresh_aviser=False):
    '''Henter urler til alle kundeavis-sider i kupp.vg, og returnerer en dict med butikker som key og liste med urler som value.
    
    Dersom refresh_aviser == True vil programmet forsøke å laste ned ny html-kode fra kupp.vg.no.
    '''

    curr_date, år, uke = dato

    htmlDirectory = f"temp_output/kupphtml_{år}_{uke}.txt"

    downloaded_shops = []

    '''
    try:
        for entry in os.listdir(f'kundeavis_data/{år}_{uke}'):
            shopName = entry.split('_')[0]
            if shopName not in downloaded_shops:
                downloaded_shops.append(shopName)
        
        BUTIKKER = list(set(BUTIKKER).difference(set(downloaded_shops)))
        if not BUTIKKER:
            print('Kundeavisene til valgte butikker er allerede lasted ned')
            return None
    except:
        pass
    '''


    if refresh_aviser:
        url = "https://kupp.vg.no/"

        page = urlopen(url)

        html_bytes = page.read()
        html = html_bytes.decode("utf-8")

        with open(htmlDirectory, 'w', encoding='utf-8') as fil:
            fil.write(html)
            print('file written successfully!')
        
    else:
        with open(htmlDirectory, 'r') as fil:
            html = fil.read()
    
    kundeavisen = {}
    kundeavisen['header'] = [år, uke, BUTIKKER]





    for butikk in BUTIKKER:

        avis_src = "https://s.kupp.no/prod/pages/" + butikk + "/" + str(år) + "/" + str(uke) + "/"

        word = avis_src
        occurrences = []

        # Using re.finditer to get match objects with start and end indices
        for match in re.finditer(word, html):
            occurrences.append((match.start(), match.end()))
        src_occurrences = []

        extr_str_len = len('b372bf52-db70-44a0-8e4b-215d2fb74d9f.t')

        #TODO: BRUK HELLER if '.jpg' in str
        for occ_idx_strt, occ_idx_end in occurrences:
            if '.t' in html[occ_idx_strt:occ_idx_end+extr_str_len]:
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
            save_location = f"temp_output/bilder/{butikk}_{år}_{uke}_{idx}.jpg" 
            download_from_url(url, save_location)