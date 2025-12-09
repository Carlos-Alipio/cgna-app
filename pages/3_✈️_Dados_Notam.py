import streamlit as st
import pandas as pd
import requests
import xmltodict
from sqlalchemy import text # Necessário para comandos SQL manuais

st.set_page_config(page_title="Extração Supabase", layout="wide")
st.title("✈️ Importador de NOTAMs (PostgreSQL/Supabase)")

# --- CONFIGURAÇÕES ---
# Pegando a senha do cofre de segredos (secrets.toml)
# O nome "supabase" aqui deve ser o mesmo que você colocou nos colchetes [connections.supabase]
conn = st.connection("supabase", type="sql")

API_KEY = "1279934730"
API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"
BASE_URL = "http://aisweb.decea.mil.br/api/"

# --- FUNÇÕES DO BANCO DE DADOS (AGORA COM POSTGRES) ---
def salvar_no_banco(df):
    try:
        with conn.session as s:
            # if_exists='replace' -> CRUCIAL AGORA: 
            # Isso vai destruir a tabela antiga (com poucas colunas)
            # e criar a nova automaticamente com TODAS as colunas do XML.
            df.to_sql('notams', conn.engine, if_exists='replace', index=False, chunksize=1000)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def ler_do_banco():
    # O st.connection tem cache automático (ttl). 
    # ttl=0 garante que sempre pegue o dado fresco.
    try:
        df = conn.query('SELECT * FROM notams', ttl=0)
        return df
    except:
        return pd.DataFrame()

# --- BUSCA NA API (Mesma lógica de antes) ---
# --- FUNÇÃO DE EXTRAÇÃO (VERSÃO SALVA TUDO) ---
def buscar_notams(icao_code):
    headers = {'Content-Type': 'application/xml'}
    params = {'apiKey': API_KEY, 'apiPass': API_PASS, 'area': 'notam', 'icaocode': icao_code}
    
    with st.spinner(f"Baixando TUDO de {icao_code}..."):
        response = requests.get(BASE_URL, params=params)
    
    if response.status_code == 200:
        dados_dict = xmltodict.parse(response.content)
        try:
            # Caminho para achar os itens no XML
            if 'aisweb' in dados_dict and 'notam' in dados_dict['aisweb'] and 'item' in dados_dict['aisweb']['notam']:
                lista_notams = dados_dict['aisweb']['notam']['item']
            else:
                return None

            # Garante que seja lista mesmo se tiver só 1 item
            if isinstance(lista_notams, dict): lista_notams = [lista_notams]
            
            # 1. Cria o DataFrame com TODAS as colunas que vierem
            df = pd.DataFrame(lista_notams)
            
            # 2. TRUQUE DE MESTRE: Converter tudo para String (Texto)
            # O XML tem dados aninhados (dicionários dentro de dicionários).
            # O PostgreSQL não aceita dicionário Python direto.
            # Convertendo pra string, garantimos que nada quebra o salvamento.
            df = df.astype(str)
            
            return df
            
        except Exception as e:
            st.error(f"Erro ao processar dados: {e}")
            return None
    return None

# --- INTERFACE ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Gravar na Nuvem")
    aeroporto = st.text_input("ICAO", value="SBGR")
    
    if st.button("Buscar e Salvar no Supabase"):
        df_novo = buscar_notams(aeroporto)
        if df_novo is not None and not df_novo.empty:
            sucesso = salvar_no_banco(df_novo)
            if sucesso:
                st.success("✅ Dados salvos no Supabase com sucesso!")
        else:
            st.warning("Nada encontrado.")

with col2:
    st.subheader("2. Ler da Nuvem")
    st.write("Dados vindo direto do Data Center em São Paulo.")
    
    df_banco = ler_do_banco()
    if not df_banco.empty:
        st.dataframe(df_banco)
    else:
        st.info("Banco vazio.")