import streamlit as st
import pandas as pd
from sqlalchemy import text

# Conexão centralizada
def get_connection():
    return st.connection("supabase", type="sql")

def salvar_notams(df):
    conn = get_connection()
    try:
        with conn.session as s:
            df.to_sql('notams', conn.engine, if_exists='replace', index=False, chunksize=1000)
        return True
    except Exception as e:
        st.error(f"Erro no Banco: {e}")
        return False

def carregar_notams():
    conn = get_connection()
    try:
        return conn.query('SELECT * FROM notams', ttl=0)
    except:
        return pd.DataFrame()

def carregar_frota_monitorada():
    conn = get_connection()
    try:
        df = conn.query("SELECT icao FROM frota_icao", ttl=0)
        return df['icao'].tolist() if not df.empty else []
    except:
        return []