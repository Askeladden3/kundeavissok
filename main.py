
from Gemini_Parser import Gemini_parser
from fromJSONtoSQlite import JSONtoSQlite
from kundeavis_fetch import fetch_kundeavis, download_kundeaviser
import datetime
from networking import updateWebsite, create_frontend_files, updateWebsite_testing, zip_and_saveFiles

def main(params):

    Alle_butikker = ['meny', 'rema-1000', 'kiwi', 'extra','bunnpris','coop-prix','joker','spar','coop-mega','coop-marked','obs']
    #TODO 1: om ny_uke = True bør programmet likevel sjekke om kundeavisbilder er lastet ned fra før, og at om de er det så hopper den over nedlastningen
    if not params['BUTIKKER']:
        BUTIKKER = Alle_butikker
    else:
        BUTIKKER = params['BUTIKKER']
    


    current_date = datetime.datetime.now()
    år = current_date.year
    uke = current_date.date().isocalendar()[1]

    dato = [current_date, år, uke]


    if params['download_kundeaviser']:
        avisurls = fetch_kundeavis(BUTIKKER, dato, refresh_aviser = True)
        if avisurls:
            download_kundeaviser(dato, avisurls)


    if not params['skip_parsing']:
        Gemini_parser(BUTIKKER, dato, params['add_temp_JSON'], params['batch_processing'], params['batchsize'])
    nedlastede_butikker = JSONtoSQlite(dato)


    create_frontend_files(uke, Alle_butikker, nedlastede_butikker)

    if params['test_mode']:
        updateWebsite_testing(uke)

    elif params['updateWebsite']:
        updateWebsite(uke)

    if params['saveFiles']:
        zip_and_saveFiles(dato)



ny_uke_standard = {
    'test_mode': False,
    'BUTIKKER': None,
    'download_kundeaviser': True,
    'skip_parsing': False,
    'batch_processing':True,
    'batchsize': 14,
    'add_temp_JSON': False, 
    'saveFiles': True,
    'updateWebsite': True
    
}

testing_stuff = {
    'test_mode': False,
    'BUTIKKER': None,
    'download_kundeaviser': False,
    'skip_parsing': False,
    'batch_processing':True,
    'batchsize': 18,
    'add_temp_JSON': False, 
    'saveFiles': True,
    'updateWebsite': False
    
}

main(testing_stuff)