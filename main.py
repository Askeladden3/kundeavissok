
from Gemini_Parser import Gemini_parser
from fromJSONtoSQlite import JSONtoSQlite
from kundeavis_fetch import fetch_kundeavis, download_kundeaviser
import datetime

def main(ny_uke = False, BUTIKKER=None, append_til_JSON = True, skip_parsing = False):
    if not BUTIKKER:
        BUTIKKER = ['rema-1000', 'kiwi', 'extra','bunnpris','meny','coop-prix','joker','spar','coop-mega','naerbutikken','coop-marked','obs']

    if ny_uke:
        avisurls = fetch_kundeavis(BUTIKKER, refresh_aviser = True)
        download_kundeaviser(avisurls)
    
    current_date = datetime.datetime.now()
    år = current_date.year
    uke = current_date.date().isocalendar()[1]


    if not append_til_JSON or ny_uke:
        write_mode = 'replace'
    else:
        write_mode = 'add'
    
    if not skip_parsing:
        Gemini_parser(BUTIKKER, uke, write_mode)
    JSONtoSQlite(uke)



#EKSEMPELKJØRINGER:

#OPPDATER DATABASE TIL NY UKE (Lager også ny database-fil):
# main(ny_uke = True)

#LEGG TIL EN ENKELT BUTIKK PÅ ALLEREDE EKSISTERENDE JSON-FILER (F. eks dersom en butikk var treg med å legge ut kundeavisen sin)
#main(BUTIKKER=['kiwi'], append_til_JSON = True)

#KUN LAGE NY DATABASE-FIL / KJØR JSONtoSQlite:
#main(skip_parsing=True)


