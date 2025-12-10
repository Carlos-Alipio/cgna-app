import streamlit as st
import pandas as pd
from sqlalchemy import text

# --- CONEXÃO CENTRALIZADA ---
def get_connection():
    return st.connection("supabase", type="sql")

# --- GERENCIAMENTO DE NOTAMS ---
def salvar_notams(df):
    conn = get_connection()
    try:
        with conn.session as s:
            with st.spinner(f"💾 Salvando {len(df)} registros no banco de dados..."):
                df.to_sql(
                    'notams', 
                    conn.engine, 
                    if_exists='replace', 
                    index=False, 
                    chunksize=500, 
                    method='multi'
                )
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Banco: {e}")
        return False

def carregar_notams():
    conn = get_connection()
    try:
        return conn.query('SELECT * FROM notams', ttl=0)
    except:
        return pd.DataFrame()

# --- GERENCIAMENTO DE FROTA (ICAO) ---
def carregar_frota_monitorada():
    conn = get_connection()
    try:
        df = conn.query("SELECT icao FROM frota_icao", ttl=0)
        return df['icao'].tolist() if not df.empty else []
    except:
        return []

def adicionar_icao(icao, desc):
    conn = get_connection()
    try:
        with conn.session as s:
            s.execute(
                text("INSERT INTO frota_icao (icao, descricao) VALUES (:i, :d)"),
                params={"i": icao.upper().strip(), "d": desc}
            )
            s.commit()
        return True
    except:
        return False

def remover_icao(icao):
    conn = get_connection()
    try:
        with conn.session as s:
            s.execute(
                text("DELETE FROM frota_icao WHERE icao = :i"),
                params={"i": icao}
            )
            s.commit()
        return True
    except:
        return False

# --- GERENCIAMENTO DE FILTROS CRÍTICOS (AS NOVAS FUNÇÕES) ---

def carregar_filtros_configurados():
    """Retorna um DataFrame com todos os filtros salvos"""
    conn = get_connection()
    try:
        return conn.query("SELECT * FROM config_filtros", ttl=0)
    except:
        # Se a tabela não existir ou estiver vazia, retorna estrutura vazia
        return pd.DataFrame(columns=['tipo', 'valor'])

def atualizar_filtros_lote(tipo, lista_valores):
    """
    Apaga os filtros antigos desse tipo e insere os novos.
    tipo: 'assunto' ou 'condicao'
    lista_valores: lista de strings selecionadas
    """
    conn = get_connection()
    try:
        with conn.session as s:
            # 1. Limpa os filtros anteriores desse tipo
            s.execute(text("DELETE FROM config_filtros WHERE tipo = :t"), params={"t": tipo})
            
            # 2. Insere os novos (se houver)
            if lista_valores:
                dados = [{"t": tipo, "v": v} for v in lista_valores]
                s.execute(
                    text("INSERT INTO config_filtros (tipo, valor) VALUES (:t, :v)"),
                    dados
                )
            s.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar filtros: {e}")
        return False