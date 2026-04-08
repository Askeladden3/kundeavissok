import os
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, Integer, String, Float, text


def JSONtoSQlite(cfg):


    default_column_types = {
    'name': String(355),
    'brand': String(100),
    'total_mass': Float(),
    'unit': String(30),
    'store': String(30),
    'brand': String(50),
    'category': String(50),
    'protein_type': String(25),
    'AI_model_used': String(100),
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
    USER = os.environ['DB_USER']
    PASSWORD = os.environ['DB_PASS']
    HOST = os.environ['DB_HOST']
    PORT = '3306'
    DATABASE = os.environ['DB_NAME']
    engine = create_engine(f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}")

    for entry in os.scandir(JSON_dirpath):
        if entry.is_file():
            json_file = entry.path
            data = pd.read_json(json_file)
            table_name = entry.name.split('.')[0]
            deal_type = table_name

            if cfg['test_mode']:
                table_name = 'TEST' + table_name

            if data.empty:
                with engine.connect() as conn:
                    conn.execute(text(f'TRUNCATE TABLE {table_name};'))
                    conn.commit()
                    continue

            data.drop(columns=['deal_type'], inplace=True)
            if 'protein_type' in data.columns:
                data['protein_type'] = data['protein_type'].map(protein_dict)


            data.to_sql(name=table_name,
                    con=engine,
                    index=False,
                    if_exists= 'append' if cfg['append_SQL'] else 'replace',
                    dtype=db_types[deal_type])
            
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