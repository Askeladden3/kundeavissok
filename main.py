
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
        Gemini_parser(BUTIKKER, dato, params['add_temp_JSON'])
    nedlastede_butikker = JSONtoSQlite(dato)


    create_frontend_files(uke, Alle_butikker, nedlastede_butikker)

    if params['test_mode']:
        updateWebsite_testing(uke)

    elif params['updateWebsite']:
        updateWebsite(uke)

    if params['saveFiles']:
        zip_and_saveFiles(dato)



ny_uke_standard = {
    'BUTIKKER': None,
    'download_kundeaviser': True,
    'test_mode': False,
    'add_temp_JSON': True, 
    'skip_parsing': False,
    'saveFiles': True,
    'updateWebsite': True
}

#EKSEMPELKJØRINGER:

#OPPDATER DATABASE TIL NY UKE (Lager også ny database-fil):
main(ny_uke_standard)


#LAGE NY DATABASE-FIL / KJØR JSONtoSQlite:
#main(skip_parsing=True)

#LEGGE TIL EN ENKELT BUTIKK PÅ ALLEREDE EKSISTERENDE JSON-FILER (F. eks dersom en butikk var treg med å legge ut kundeavisen sin)
#main(BUTIKKER=['joker'], append_til_JSON = True, ny_uke = True)

