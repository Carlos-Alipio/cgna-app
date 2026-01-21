import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta

# --- CONEXÃO CENTRALIZADA ---
def get_connection():
    return st.connection("supabase", type="sql")

# --- GERENCIAMENTO DE NOTAMS ---
def salvar_notams(df):
    conn = get_connection()
    
    # ==============================================================================
    # 🛠️ HOOK DE CORREÇÃO: REGRA PERM (B + 365 DIAS)
    # ==============================================================================
    try:
        # Garante datetime para cálculos
        df['b_dt'] = pd.to_datetime(df['b'], errors='coerce')
        
        def corrigir_data_fim(row):
            # Pega valor bruto do campo C e data de início B
            data_c_raw = str(row.get('c', '')).upper()
            dt_inicio = row['b_dt']
            
            if pd.isna(dt_inicio):
                return row['c'] 
            
            # REGRA ÚNICA: Se tiver "PERM" no campo C -> Início + 365 dias
            if "PERM" in data_c_raw:
                return dt_inicio + timedelta(days=365)
            
            # Caso contrário, mantém o original
            return row['c']

        if set(['b', 'c']).issubset(df.columns):
            df['c'] = df.apply(corrigir_data_fim, axis=1)
        
        if 'b_dt' in df.columns:
            df = df.drop(columns=['b_dt'])
            
    except Exception as e:
        print(f"Aviso: Erro na correção PERM: {e}")
    
    # ==============================================================================

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

# --- GERENCIAMENTO DE FILTROS CRÍTICOS ---
def carregar_filtros_configurados():
    conn = get_connection()
    try:
        return conn.query("SELECT * FROM config_filtros", ttl=0)
    except:
        return pd.DataFrame(columns=['tipo', 'valor'])

def atualizar_filtros_lote(tipo, lista_valores):
    conn = get_connection()
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM config_filtros WHERE tipo = :t"), params={"t": tipo})
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