import streamlit as st
import pandas as pd
import requests
import xmltodict
import sqlite3

st.set_page_config(page_title="Extração API DECEA", layout="wide")

st.title("✈️ Importador de NOTAMs (DECEA)")

# --- CONFIGURAÇÕES DA API ---
# DICA: Em projetos reais, guarde isso no st.secrets ou variáveis de ambiente
API_KEY = "1279934730"
API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"
BASE_URL = "http://aisweb.decea.mil.br/api/"

# --- FUNÇÕES DE BANCO DE DADOS (SQLITE) ---
def salvar_no_banco(df):
    # Cria/Conecta ao arquivo 'dados_aereos.db'
    conn = sqlite3.connect('dados_aereos.db')
    
    # Salva o DataFrame como uma tabela SQL chamada 'notams'
    # if_exists='replace' -> Apaga a tabela antiga e cria uma nova
    # if_exists='append'  -> Adiciona os dados novos embaixo dos antigos
    df.to_sql('notams', conn, if_exists='replace', index=False)
    
    conn.close()
    return True

def ler_do_banco():
    conn = sqlite3.connect('dados_aereos.db')
    try:
        df = pd.read_sql('SELECT * FROM notams', conn)
    except:
        df = pd.DataFrame() # Retorna vazio se não tiver banco ainda
    conn.close()
    return df

# --- FUNÇÃO DE EXTRAÇÃO (A MÁGICA) ---
def buscar_notams(icao_code):
    """
    Busca NOTAMs de um aeroporto específico (ex: SBGR, SBRJ)
    """
    headers = {'Content-Type': 'application/xml'}
    params = {
        'apiKey': API_KEY,
        'apiPass': API_PASS,
        'area': 'notam',
        'icaocode': icao_code  # O DECEA exige um filtro (Aeroporto)
    }
    
    with st.spinner(f"Conectando ao DECEA para buscar dados de {icao_code}..."):
        response = requests.get(BASE_URL, params=params)
    
    if response.status_code == 200:
        # A API retorna XML. Usamos xmltodict para virar Dicionário Python
        dados_dict = xmltodict.parse(response.content)
        
        # Navegando no XML para achar a lista de notams:
        # Estrutura típica: <aisweb><notam><item>...</item></notam></aisweb>
        try:
            lista_notams = dados_dict['aisweb']['notam']['item']
            
            # Se vier só 1 notam, o xmltodict não cria lista, cria um dict direto.
            # Precisamos garantir que seja uma lista para o Pandas.
            if isinstance(lista_notams, dict):
                lista_notams = [lista_notams]
                
            # Cria o DataFrame
            df = pd.DataFrame(lista_notams)
            
            # Selecionando colunas mais úteis (opcional)
            colunas_uteis = ['id', 'number', 'tipo', 'dt_iniciovigencia', 'dt_terminovigencia', 'texto']
            # Filtra só as colunas que existem no DF
            cols = [c for c in colunas_uteis if c in df.columns]
            
            return df[cols]
            
        except KeyError:
            st.warning("A API respondeu, mas não encontrou NOTAMs ou a estrutura mudou.")
            return None
    else:
        st.error(f"Erro na conexão: {response.status_code}")
        return None

# --- INTERFACE DO USUÁRIO ---

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Extrair Dados")
    aeroporto = st.text_input("Código ICAO (ex: SBGR, SBRJ, SBMT)", value="SBGR,SBKP,SBGL,SBSP,SBAR")
    
    if st.button("Buscar e Salvar no Banco"):
        df_novo = buscar_notams(aeroporto)
        
        if df_novo is not None and not df_novo.empty:
            salvar_no_banco(df_novo)
            st.success(f"{len(df_novo)} NOTAMs salvos no banco de dados!")
        else:
            st.info("Nenhum dado encontrado para salvar.")

with col2:
    st.subheader("2. Visualizar Banco de Dados")
    st.write("Estes dados estão sendo lidos diretamente do arquivo `dados_aereos.db`")
    
    df_banco = ler_do_banco()
    
    if not df_banco.empty:
        st.dataframe(df_banco, use_container_width=True)
    else:
        st.info("O banco de dados está vazio. Faça uma busca ao lado.")