import os
import json
import base64
import time
from datetime import datetime
import sqlite3



def JSONtoSQlite(dato):

    curr_date, år, UKE = dato

    os.mkdir('temp_output/databaser')
    db_file = f'temp_output/databaser/kundeavis_{UKE}.db'

    def EXECUTE_TABLES(item, table_name):
        dato = datetime.strptime(f'{år} {UKE} 1', '%G %V %u').date()

        if table_name == 'kroner_off_deals':
            table = ['''
                INSERT INTO kroner_off_deals (name, amount_subtracted, store, avis_date, page_number)
                VALUES (?, ?, ?, ?, ?)
            ''', (item['name'], item['amount_subtracted'], item['store'], dato, item['page_number'])]
        elif table_name == 'multibuy_for_price_deals':
            table = ['''
                INSERT INTO multibuy_for_price_deals (name, amount_of_wares, set_price, store, avis_date, page_number)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (item['name'], item['amount_of_wares'], item['set_price'], item['store'], dato, item['page_number'])]

        elif table_name == 'percentage_deals':
            table = ['''
                INSERT INTO percentage_deals (name, percentage_off, store, avis_date, page_number)
                VALUES (?, ?, ?, ?, ?)
            ''', (item['name'], item['percentage_off'], item['store'], dato, item['page_number'])]

        elif table_name =='price_deals':
            table = ['''
                INSERT INTO price_deals (name, total_price, price_per_unit, total_mass, store, unit, avis_date, page_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item['name'], item['total_price'], item['price_per_unit'], item['total_mass'], item['store'], item['unit'], dato, item['page_number'])]

        elif table_name == 'three_for_two_deals':
            table = ['''
                INSERT INTO three_for_two_deals (name, store, avis_date, page_number)
                VALUES (?, ?, ?, ?)
            ''', (item['name'], item['store'], dato, item['page_number'])]


        return table
    
    def CREATE_TABLE(table_name):
        tableDict = {
            'kroner_off_deals' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT,
                amount_subtracted INTEGER NOT NULL,
                store TEXT NOT NULL,
                avis_date DATE,
                page_number INTEGER
                )''',

            'multibuy_for_price_deals' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT,
                amount_of_wares INTEGER NOT NULL,
                set_price DECIMAL(10,3) NOT NULL,
                store TEXT NOT NULL,
                avis_date DATE,
                page_number INTEGER
                )''',

            'percentage_deals' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT,
                percentage_off INTEGER NOT NULL,
                store TEXT NOT NULL,
                avis_date DATE,
                page_number INTEGER
                )''',

            'price_deals' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT,
                total_price DECIMAL (10,2),
                price_per_unit DECIMAL (10,2),
                total_mass DECIMAL (8,3),
                store TEXT NOT NULL,
                unit TEXT DEFAULT 'kg',
                avis_date DATE,
                page_number INTEGER
                )''',
                
            'three_for_two_deals' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT,
                store TEXT NOT NULL,
                avis_date DATE,
                page_number INTEGER
                )'''}
        
        return tableDict[table_name]
    
    def CREATE_SEARCH_TABLE(table_name):
        SQdict = {'kroner_off_deals' :        ["CREATE VIRTUAL TABLE IF NOT EXISTS kroner_off_deals_fts USING fts5(name, content='kroner_off_deals', content_rowid='id')",
                                               "INSERT INTO kroner_off_deals_fts(rowid, name) SELECT id, name FROM kroner_off_deals;"],

                  'price_deals':              ["CREATE VIRTUAL TABLE IF NOT EXISTS price_deals_fts USING fts5(name, content='price_deals', content_rowid='id');",
                                               "INSERT INTO price_deals_fts(rowid, name) SELECT id, name FROM price_deals;",],

                  'multibuy_for_price_deals': ["CREATE VIRTUAL TABLE IF NOT EXISTS multibuy_for_price_deals_fts USING fts5(name, content='multibuy_for_price_deals', content_rowid='id');",
                                               "INSERT INTO multibuy_for_price_deals_fts(rowid, name) SELECT id, name FROM multibuy_for_price_deals;",],
                
                  'percentage_deals':         ["CREATE VIRTUAL TABLE IF NOT EXISTS percentage_deals_fts USING fts5(name, content='percentage_deals', content_rowid='id');",
                                               "INSERT INTO percentage_deals_fts(rowid, name) SELECT id, name FROM percentage_deals;",],
                                               
                  'three_for_two_deals':      ["CREATE VIRTUAL TABLE IF NOT EXISTS three_for_two_deals_fts USING fts5(name, content='three_for_two_deals', content_rowid='id');",
                                               "INSERT INTO three_for_two_deals_fts(rowid, name) SELECT id, name FROM three_for_two_deals;"]}
        SQcommands = SQdict[table_name]

        for command in SQcommands:
            print(command)
            cursor.execute(command)




    JSON_dirpath = f'temp_output/results_JSON'

    for entry in os.scandir(JSON_dirpath):
        if entry.is_file():
            json_file = entry.path
            table_name = json_file.split('/')[2][:-5]

            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                unique_deals = {}
                for vare in data:
                #Denne løkken fjerner duplikatvarer fra JSON-filene
                    navn = vare['name'].lower()

                    if navn not in unique_deals:
                        unique_deals[navn] = [vare]
                    else:
                        unique = True
                        for enkelt_deal in unique_deals[navn]:
                            if vare['store'] == enkelt_deal['store']:
                                unique = False
                                break
                        if unique:
                            unique_deals[navn].append(vare)

                processed_data = []
                for vare_kombo in unique_deals.values():
                    for vare in vare_kombo:
                        processed_data.append(vare)





            cursor.execute(CREATE_TABLE(table_name))
            conn.commit()


            for item in processed_data:

                sqlite_command, sqlite_data = EXECUTE_TABLES(item, table_name)
                cursor.execute(sqlite_command, sqlite_data)
            
            CREATE_SEARCH_TABLE(table_name)

            conn.commit()

    