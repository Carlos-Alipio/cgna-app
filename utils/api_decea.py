import requests
import xmltodict
import pandas as pd
import streamlit as st
# Importa o formatters para já salvar o dado limpo/decodificado
from utils.formatters import decodificar_q_code

API_KEY = "1279934730"
API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"
BASE_URL = "http://aisweb.decea.mil.br/api/"

def buscar_por_lista(lista_icaos):
    """
    Recebe uma lista ['SBGR', 'SBSP'] e busca apenas eles na API.
    Isso torna o download MUITO mais rápido.
    """
    if not lista_icaos:
        return None

    # Transforma a lista em string separada por vírgula (ex: "SBGR,SBSP,SBRJ")
    # O .join garante que não haja espaços extras
    icaos_string = ",".join([str(x).strip().upper() for x in lista_icaos])
    
    headers = {'Content-Type': 'application/xml'}
    params = {
        'apiKey': API_KEY, 
        'apiPass': API_PASS, 
        'area': 'notam', 
        'icaocode': icaos_string
    }
    
    with st.spinner(f"📡 Baixando dados de {len(lista_icaos)} aeroportos da sua lista..."):
        try:
            # timeout=30 evita que o sistema fique travado eternamente se a API cair
            response = requests.get(BASE_URL, params=params, timeout=30)
            
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
        # Navegação segura no XML para achar a lista de itens
        if 'aisweb' in dados_dict and 'notam' in dados_dict['aisweb'] and 'item' in dados_dict['aisweb']['notam']:
            lista = dados_dict['aisweb']['notam']['item']
            
            # Se vier só 1 notam, transforma em lista para não dar erro no Pandas
            if isinstance(lista, dict): lista = [lista]
            
            df = pd.DataFrame(lista)
            
            # --- PROCESSAMENTO (DECODIFICAÇÃO) ---
            # Já aplicamos a tradução aqui para salvar no banco pronto
            col_q = next((c for c in ['cod', 'code', 'q'] if c in df.columns), None)
            
            if col_q:
                df['assunto_desc'], df['condicao_desc'], df['assunto_cod'], df['condicao_cod'] = \
                    zip(*df[col_q].apply(decodificar_q_code))
            else:
                df['assunto_desc'] = "N/A"
                df['condicao_desc'] = "N/A"
            
            return df.astype(str)
            
        return pd.DataFrame() # Retorna vazio se não tiver NOTAMs (ex: aeroporto sem avisos)
        
    except Exception as e:
        st.error(f"Erro ao ler XML: {e}")
        return None