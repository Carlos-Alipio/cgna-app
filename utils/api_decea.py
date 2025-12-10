import requests
import xmltodict
import pandas as pd
import streamlit as st
from utils.formatters import decodificar_q_code

API_KEY = "1279934730"
API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"
BASE_URL = "http://aisweb.decea.mil.br/api/"

def buscar_firs_brasil():
    """
    Busca as 5 FIRs do Brasil.
    Isso traz TODOS os NOTAMs do espaço aéreo brasileiro.
    """
    # FIRs: Amazônica, Brasília, Curitiba, Recife, Atlântico
    firs = "SBAZ,SBBS,SBCW,SBRE,SBQV"
    
    headers = {'Content-Type': 'application/xml'}
    params = {
        'apiKey': API_KEY, 
        'apiPass': API_PASS, 
        'area': 'notam', 
        'icaocode': firs
    }
    
    with st.spinner(f"📡 Baixando dados completos do espaço aéreo brasileiro (5 FIRs)..."):
        try:
            # Aumentei o timeout para 60s pois o arquivo é grande
            response = requests.get(BASE_URL, params=params, timeout=60)
            
            if response.status_code == 200:
                return processar_xml(response.content)
            else:
                st.error(f"Erro na API do DECEA: {response.status_code}")
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
            
            # Decodificação do Código Q
            col_q = next((c for c in ['cod', 'code', 'q'] if c in df.columns), None)
            
            if col_q:
                df['assunto_desc'], df['condicao_desc'], df['assunto_cod'], df['condicao_cod'] = \
                    zip(*df[col_q].apply(decodificar_q_code))
            else:
                df['assunto_desc'] = "N/A"
                df['condicao_desc'] = "N/A"
            
            return df.astype(str)
            
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Erro ao ler XML: {e}")
        return None