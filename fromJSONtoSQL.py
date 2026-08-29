import os
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, Integer, String, Float, text
import yaml


def JSONtoPostgres(cfg):


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
        'standard_deal': standard_deal_types,
        'percentage_deal': percentage_deal_types,
        'bogo_deal': bogo_deal_types
    }

    protein_dict = {None: None, "beef": "Ku", "pork": "Svin", "poultry": "Kylling", "lamb": "Lam", "mixed": "Blandet", "plant_based": "Plante-basert"}
    JSON_dirpath = f'temp_output/results_JSON'

    unique_stores = set()

    engine = create_engine(os.environ["DB_URL"])

    for entry in os.scandir(JSON_dirpath):
        if entry.is_file():
            json_file = entry.path
            data = pd.read_json(json_file, encoding='utf-8')
            table_name = entry.name.split('.')[0]
            deal_type = table_name

            if cfg['test_mode']:
                table_name = 'TEST' + table_name

            if data.empty:
                with engine.connect() as conn:
                    conn.execute(text(f'TRUNCATE TABLE "{table_name}";'))
                    conn.commit()
                    continue

            data.drop(columns=['deal_type'], inplace=True)
            if 'protein_type' in data.columns:
                data['protein_type'] = data['protein_type'].map(protein_dict)

            if not cfg['append_SQL']:
                with engine.connect() as conn:
                    conn.execute(text(f'TRUNCATE TABLE "{table_name}"'))
                    conn.commit()

            data.to_sql(name=table_name,
                        con=engine,
                        index=False,
                        if_exists='append',
                        dtype=db_types[deal_type])

            stores = set(data['store'])
            unique_stores = unique_stores.union(stores)

    return unique_stores


if __name__ == '__main__':
    
    with open('config.yaml', 'r') as fil:
        cfg = yaml.safe_load(fil)
    current_date = datetime.now()
    år = current_date.year
    uke = current_date.date().isocalendar()[1]
    dato = [current_date, år, uke]

    JSONtoPostgres(cfg['standard'])