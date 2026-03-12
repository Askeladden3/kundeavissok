import pandas as pd
import os
import json
import base64
import time
from datetime import datetime
import sqlite3

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
            price_per_unit DECIMAL (10,2),
            total_price DECIMAL (10,2),
            total_mass DECIMAL (8,3),
            unit TEXT DEFAULT 'kg',
            store TEXT NOT NULL,
            acquired_date DATE,
            page_number INTEGER,
            AI_model_used TEXT
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


db_file = r'temp_output\kundeavis_4.db'


A = pd.read_json(r'temp_output\price_deals.json')

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

cursor.execute(CREATE_TABLE('price_deals'))
conn.commit()



A.to_sql(name='price_deals',
        con=conn,
        index=False,
        if_exists='append')