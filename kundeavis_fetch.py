from urllib.request import urlopen
import re
from datetime import datetime
import requests
import json
import os

def fetch_kundeavis(BUTIKKER, dato, refresh_aviser=False):
    '''Henter urler til alle kundeavis-sider i kupp.vg, og returnerer en dict med butikker som key og liste med urler som value.
    
    Dersom refresh_aviser == True vil programmet forsøke å laste ned ny html-kode fra kupp.vg.no.
    '''

    curr_date, år, uke = dato

    htmlDirectory = f"temp_output/kupphtml_{år}_{uke}.txt"

    downloaded_shops = []
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


def download_kundeaviser(dato, kundeaviser_urls):

    current_date, år, uke = dato

    print('Header for valgt kundeavis: ' , kundeaviser_urls['header'])

    try:
        os.mkdir(f'temp_output/kundeaviser/{år}_{uke}')
    except:
        pass

    def download_from_url(url,save_path):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

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
            save_location = f"temp_output/kundeaviser/{år}_{uke}/{butikk}_2025_{uke}_{idx}.jpg" 
            download_from_url(url, save_location)


