import requests
import xmltodict
import pandas as pd
import streamlit as st
from utils.formatters import decodificar_q_code # Reusa a lógica

# Constantes (Idealmente mover para st.secrets, mas pode ficar aqui)
API_KEY = "1279934730"
API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"
BASE_URL = "http://aisweb.decea.mil.br/api/"

def buscar_firs_brasil():
    """Busca as 5 FIRs principais"""
    return buscar_na_api("SBAZ,SBBS,SBCW,SBRE,SBQV")

def buscar_na_api(icao_code):
    headers = {'Content-Type': 'application/xml'}
    params = {'apiKey': API_KEY, 'apiPass': API_PASS, 'area': 'notam', 'icaocode': icao_code}
    
    with st.spinner(f"📡 Conectando ao DECEA ({icao_code})..."):
        try:
            response = requests.get(BASE_URL, params=params, timeout=45)
            if response.status_code == 200:
                return processar_xml(response.content)
            else:
                st.error(f"Erro API: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            return None

def processar_xml(content):
    dados_dict = xmltodict.parse(content)
    try:
        if 'aisweb' in dados_dict and 'notam' in dados_dict['aisweb'] and 'item' in dados_dict['aisweb']['notam']:
            lista = dados_dict['aisweb']['notam']['item']
            if isinstance(lista, dict): lista = [lista]
            
            df = pd.DataFrame(lista)
            
            # Aplica a decodificação do código Q aqui mesmo
            col_q = next((c for c in ['cod', 'code', 'q'] if c in df.columns), None)
            if col_q:
                df['assunto_desc'], df['condicao_desc'], _, _ = zip(*df[col_q].apply(decodificar_q_code))
            else:
                df['assunto_desc'] = "N/A"
                df['condicao_desc'] = "N/A"
            
            return df.astype(str)
        return None
    except Exception as e:
        st.error(f"Erro ao ler XML: {e}")
        return None