import os
import json
import base64
import time
from datetime import datetime
import sqlite3
import pandas as pd


def JSONtoSQlite(dato):

    curr_date, år, UKE = dato

    try:
        os.mkdir('temp_output/databaser')
    except:
        pass
    db_file = f'temp_output/databaser/kundeavis_{UKE}.db'

    
    def CREATE_TABLE(table_name):
        tableDict = {
            'percentage_deal' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT,
                total_mass DECIMAL (8,3),
                unit TEXT DEFAULT 'kg',
                store TEXT NOT NULL,
                page_number INTEGER,
                percentage_off INTEGER NOT NULL
                )''',

            'standard_deal' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT,
                total_mass DECIMAL (8,3),
                unit TEXT DEFAULT 'kg',
                store TEXT NOT NULL,
                page_number INTEGER,
                price_per_unit DECIMAL (10,2),
                total_price DECIMAL (10,2)
                )''',
            'bogo_deal' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT,
                total_mass DECIMAL (8,3),
                unit TEXT DEFAULT 'kg',
                store TEXT NOT NULL,
                page_number INTEGER,
                required_amount INTEGER,
                amount_free INTEGER
                )'''}
        
        return tableDict[table_name]
    
    def CREATE_SEARCH_TABLE(table_name):
        SQdict = {'standard_deal':              ["CREATE VIRTUAL TABLE IF NOT EXISTS standard_deal_fts USING fts5(name, content='standard_deal', content_rowid='id');",
                                                "INSERT INTO standard_deal_fts(rowid, name) SELECT id, name FROM standard_deal;",],

                    'percentage_deal':          ["CREATE VIRTUAL TABLE IF NOT EXISTS percentage_deal_fts USING fts5(name, content='percentage_deal', content_rowid='id');",
                                                "INSERT INTO percentage_deal_fts(rowid, name) SELECT id, name FROM percentage_deal;",],


                    'bogo_deal':                ["CREATE VIRTUAL TABLE IF NOT EXISTS bogo_deal USING fts5(name, content='bogo_deal', content_rowid='id');",
                                                "INSERT INTO bogo_deal_fts(rowid, name) SELECT id, name FROM bogo_deal;",],

                    
                                               }
        SQcommands = SQdict[table_name]

        for command in SQcommands:
            print(command)
            cursor.execute(command)




    JSON_dirpath = f'temp_output/results_JSON'


    unique_stores = set()
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    for entry in os.scandir(JSON_dirpath):
        if entry.is_file():
            json_file = entry.path
            data = pd.read_json(json_file)
            table_name = data['deal_type'][0]
            data.drop(columns=['deal_type'], inplace=True)

            cursor.execute(CREATE_TABLE(table_name))
            conn.commit()

            data.to_sql(name=table_name,
                    con=conn,
                    index=False,
                    if_exists='append')
            
            stores = set(data['store'])
            unique_stores = unique_stores.union(stores)
            
            CREATE_SEARCH_TABLE(table_name)
            conn.commit()

    return unique_stores