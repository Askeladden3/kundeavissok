import os
import json
import base64
import time
from datetime import datetime
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, Integer, String, Float, text


def JSONtoSQlite(dato):

    curr_date, år, UKE = dato

    default_column_types = {
    'name': String(355),
    'brand': String(100),
    'total_mass': Float(),
    'unit': String(30),
    'store': String(30),
    'brand': String(50),
    'category': String(),
    'protein_type': String(),
    'AI_model_used': String(),
    'page_number': Integer()
    }

    percentage_deal_types = {
        'percentage_off': Integer()
    } | default_column_types

    standard_deal_types = {
        'price_per_unit': Float()
    } | default_column_types

    bogo_deal_types = {
        'items_recieved': Integer(),
        'items_paid_for': Integer()
    } | default_column_types

    db_types = {
        'standard_deal' : standard_deal_types,
        'percentage_deal': percentage_deal_types,
        'bogo_deal' : bogo_deal_types
    }

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
                    if_exists='replace',
                    dtype=db_types[table_name])
            
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST;"))
                conn.execute(text(f"ALTER TABLE {table_name} ADD FULLTEXT(name);"))
                conn.commit()
            
            stores = set(data['store'])
            unique_stores = unique_stores.union(stores)
            

    return unique_stores

if __name__ == '__main__':
    current_date = datetime.now()
    år = current_date.year
    uke = current_date.date().isocalendar()[1]
    dato = [current_date, år, uke]

    JSONtoSQlite(dato)