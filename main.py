
from Gemini_Parser import Gemini_parser
from fromJSONtoSQlite import JSONtoSQlite
from kundeavis_fetch import download_kundeaviser, fetch_etilbudsavis
import datetime
from networking import updateWebsite, create_frontend_files, updateWebsite_testing, zip_and_saveFiles
import yaml
import os

def main(params):

    Alle_butikker = ['meny', 'rema-1000', 'kiwi', 'extra','bunnpris','coop-prix','joker','spar','coop-mega','coop-marked','obs']
    if not params['BUTIKKER']:
        BUTIKKER = Alle_butikker
    else:
        BUTIKKER = params['BUTIKKER']
    


    current_date = datetime.datetime.now()
    år = current_date.year
    uke = current_date.date().isocalendar()[1]
    dato = [current_date, år, uke]
    try:
        os.mkdir('temp_output')
    except:
        pass



    if params['download_kundeaviser']:
        avisurls = fetch_etilbudsavis(BUTIKKER, dato)
        print('DEBUG: ', avisurls)
        if avisurls:
            download_kundeaviser(dato, avisurls)

    if not params['skip_parsing']:
        Gemini_parser(BUTIKKER, dato, params['add_website_JSON'], params['batchsize'], params['prev_failed_batches'])
    nedlastede_butikker = JSONtoSQlite(params)
    create_frontend_files(uke, Alle_butikker, nedlastede_butikker)

    if params['test_mode']:
        updateWebsite_testing(uke)
    elif params['updateWebsite']:
        updateWebsite()
    if params['saveFiles']:
        zip_and_saveFiles(dato)




with open('config.yaml', 'r') as fil:
    cfg = yaml.safe_load(fil)

main(cfg[os.environ['cfg_type']])
