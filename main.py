
from Gemini_Parser import Gemini_parser
from fromJSONtoSQlite import JSONtoSQlite
from kundeavis_fetch import fetch_kundeavis, download_kundeaviser
import datetime
from networking import updateWebsite, create_frontend_files, updateWebsite_testing, zip_and_saveFiles

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


    if params['download_kundeaviser']:
        avisurls = fetch_kundeavis(BUTIKKER, dato, refresh_aviser = True)
        if avisurls:
            download_kundeaviser(dato, avisurls)


    if not params['skip_parsing']:
        Gemini_parser(BUTIKKER, dato, params['add_website_JSON'], params['batchsize'], params['prev_failed_batches'])
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
    'batchsize': 17, #Hvis satt til None brukes automatisk algoritme, så kan være lettere hvis usikker på hva som er bra
    'prev_failed_batches': None,  #Liste med failed batches som skal reprosseseres (Ikke idx, men batch_nr (altså hvis 1. batch feilet, så skriv 1 og ikke 0 i listen))
    'add_website_JSON': False, 
    'saveFiles': True,
    'updateWebsite': True
    
}

missing_stores = {
    'test_mode': False,
    'BUTIKKER': None,
    'download_kundeaviser': False,
    'skip_parsing': False,
    'batchsize': 12, #Hvis satt til None brukes automatisk algoritme, så kan være lettere hvis usikker på hva som er bra
    'prev_failed_batches': None,  #Liste med failed batches som skal reprosseseres (Ikke idx, men batch_nr (altså hvis 1. batch feilet, så skriv 1 og ikke 0 i listen))
    'add_website_JSON': True, 
    'saveFiles': True,
    'updateWebsite': True
    
}

testing_stuff = {
    'test_mode': True,
    'BUTIKKER': ['meny'],
    'download_kundeaviser': True,
    'skip_parsing': False,
    'batchsize': 30,
    'prev_failed_batches': None,
    'add_website_JSON': False, 
    'saveFiles': False,
    'updateWebsite': False
    
}

main(ny_uke_standard)