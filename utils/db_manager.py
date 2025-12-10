import streamlit as st
import pandas as pd
from sqlalchemy import text

# Conexão centralizada
def get_connection():
    return st.connection("supabase", type="sql")

def salvar_notams(df):
    conn = get_connection()
    try:
        # Abre a sessão
        with conn.session as s:
            # Dica de Performance:
            # 1. method='multi': Envia várias linhas em um único comando SQL (muito mais rápido)
            # 2. chunksize=500: Envia de 500 em 500 para não travar a memória
            
            with st.spinner(f"💾 Salvando {len(df)} registros no banco de dados..."):
                df.to_sql(
                    'notams', 
                    conn.engine, 
                    if_exists='replace', 
                    index=False, 
                    chunksize=500, # Tamanho ideal para internet comum
                    method='multi' # Turbo mode para SQL
                )
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Banco: {e}")
        return False

def carregar_notams():
    conn = get_connection()
    try:
        # ttl=0 garante que não pegue cache velho
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