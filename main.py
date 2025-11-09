
from Gemini_Parser import Gemini_parser
from fromJSONtoSQlite import JSONtoSQlite
from kundeavis_fetch import fetch_kundeavis, download_kundeaviser
import datetime
from networking import updateWebsite, create_frontend_files, updateWebsite_testing, zip_and_saveFiles

def main(ny_uke = False, BUTIKKER=None, append_til_JSON = True, skip_parsing = False):
    Alle_butikker = ['meny', 'rema-1000', 'kiwi', 'extra','bunnpris','coop-prix','joker','spar','coop-mega','coop-marked','obs']
    #TODO 1: om ny_uke = True bør programmet likevel sjekke om kundeavisbilder er lastet ned fra før, og at om de er det så hopper den over nedlastningen
    if not BUTIKKER:
        BUTIKKER = Alle_butikker


    current_date = datetime.datetime.now()
    år = current_date.year
    uke = current_date.date().isocalendar()[1]

    dato = [current_date, år, uke]


    if ny_uke:
        avisurls = fetch_kundeavis(BUTIKKER, dato, refresh_aviser = True)
        if avisurls:
            download_kundeaviser(dato, avisurls)

    write_mode = 'add'

    if not append_til_JSON:
        write_mode = 'replace'
    
    if not skip_parsing:
        Gemini_parser(BUTIKKER, dato, write_mode)
    nedlastede_butikker = JSONtoSQlite(dato)

    if ny_uke:
        create_frontend_files(uke, Alle_butikker, nedlastede_butikker)
        updateWebsite(uke)
        #updateWebsite_testing(uke)
        zip_and_saveFiles(dato)





#EKSEMPELKJØRINGER:

#OPPDATER DATABASE TIL NY UKE (Lager også ny database-fil):
main(ny_uke=True, append_til_JSON = False)


#LAGE NY DATABASE-FIL / KJØR JSONtoSQlite:
#main(skip_parsing=True)

#LEGGE TIL EN ENKELT BUTIKK PÅ ALLEREDE EKSISTERENDE JSON-FILER (F. eks dersom en butikk var treg med å legge ut kundeavisen sin)
#main(BUTIKKER=['joker'], append_til_JSON = True, ny_uke = True)

