import os
import json
import base64
import time
from datetime import datetime
import sqlite3
import pandas as pd
from sqlalchemy import create_engine


def JSONtoSQlite(dato):

    curr_date, år, UKE = dato

    try:
        os.mkdir('temp_output/databaser')
    except:
        pass
    db_file = f'temp_output/databaser/kundeavis_{UKE}.db'

    default_table_args = '''
    id INTEGER PRIMARY KEY,
    name TEXT,
    total_mass DECIMAL (8,3),
    unit TEXT DEFAULT 'kg',
    store TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    protein_type TEXT,
    AI_model_used TEXT,
    page_number INTEGER
    '''
    
    def CREATE_TABLE(table_name):
        tableDict = {
            'percentage_deal' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                {default_table_args},
                percentage_off INTEGER NOT NULL
                )''',

            'standard_deal' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                {default_table_args},
                price_per_unit DECIMAL (10,2),
                total_price DECIMAL (10,2)
                )''',
            'bogo_deal' : f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                {default_table_args},
                items_received INTEGER,
                items_paid_for INTEGER
                )'''}
        
        return tableDict[table_name]
    
    def CREATE_SEARCH_TABLE(table_name, conn):
        SQdict = {'standard_deal':              ["CREATE VIRTUAL TABLE IF NOT EXISTS standard_deal_fts USING fts5(name, content='standard_deal', content_rowid='id');",
                                                "INSERT INTO standard_deal_fts(rowid, name) SELECT id, name FROM standard_deal;",],

                    'percentage_deal':          ["CREATE VIRTUAL TABLE IF NOT EXISTS percentage_deal_fts USING fts5(name, content='percentage_deal', content_rowid='id');",
                                                "INSERT INTO percentage_deal_fts(rowid, name) SELECT id, name FROM percentage_deal;",],


                    'bogo_deal':                ["CREATE VIRTUAL TABLE IF NOT EXISTS bogo_deal_fts USING fts5(name, content='bogo_deal', content_rowid='id');",
                                                "INSERT INTO bogo_deal_fts(rowid, name) SELECT id, name FROM bogo_deal;",],

                    
                                               }
        SQcommands = SQdict[table_name]

        for command in SQcommands:
            print(command)
            conn.execute(command)


    protein_dict = {None:None, "beef" : "Ku", "pork" : "Svin", "poultry": "Kylling", "lamb" : "Lam", "mixed": "Blandet", "plant_based": "Plante-basert"}
    JSON_dirpath = f'temp_output/results_JSON'


    unique_stores = set()
    USER = os.getenv('DB_USER')
    PASSWORD = os.getenv('DB_PASS')
    HOST = os.getenv('DB_HOST')
    PORT = '3306'
    DATABASE = os.getenv('DB_NAME')
    engine = create_engine(f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}")

    for entry in os.scandir(JSON_dirpath):
        if entry.is_file():
            json_file = entry.path
            data = pd.read_json(json_file)
            table_name = data['deal_type'][0]
            data.drop(columns=['deal_type'], inplace=True)
            data['protein_type'] = data['protein_type'].map(protein_dict)


            data.to_sql(name=table_name,
                    con=engine,
                    index=False,
                    if_exists='replace')
            
            stores = set(data['store'])
            unique_stores = unique_stores.union(stores)
            
            with engine.connect() as conn:
                CREATE_SEARCH_TABLE(table_name, conn)
                conn.commit()

    return unique_stores

if __name__ == '__main__':
    current_date = datetime.now()
    år = current_date.year
    uke = current_date.date().isocalendar()[1]
    dato = [current_date, år, uke]

    JSONtoSQlite(dato)