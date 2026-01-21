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
    # 🛠️ HOOK DE CORREÇÃO: REGRA HÍBRIDA (PERM EM C **OU** CONTEXTO EM D)
    # ==============================================================================
    try:
        df['b_dt'] = pd.to_datetime(df['b'], errors='coerce')
        
        def corrigir_data_fim(row):
            data_c_raw = str(row.get('c', '')).upper()
            texto_d = str(row.get('d', '')).upper()
            dt_inicio = row['b_dt']
            
            if pd.isna(dt_inicio):
                return row['c'] 
            
            # 1. Verifica PERM no campo C (Sua regra principal)
            tem_perm_em_c = "PERM" in data_c_raw
            
            # 2. Verifica Gatilhos no Texto D (Para recuperar casos como SBRP)
            gatilhos = ["REF AIP", "REF: AIP", "AD 2", "PERM", "AIP AD"]
            tem_perm_no_texto = any(g in texto_d for g in gatilhos)
            
            # Se tiver PERM no C OU indicativo forte no texto -> 365 dias
            if tem_perm_em_c or tem_perm_no_texto:
                return dt_inicio + timedelta(days=365)
            
            return row['c']

        if set(['b', 'c', 'd']).issubset(df.columns):
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
                    if_exists='replace', # Isso já substitui a tabela inteira
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

# --- NOVA FUNÇÃO: LIMPEZA TOTAL ---
def limpar_tabela_notams():
    """Apaga todos os registros da tabela NOTAMS"""
    conn = get_connection()
    try:
        with conn.session as s:
            # TRUNCATE é mais rápido e reseta a tabela completamente
            s.execute(text("TRUNCATE TABLE notams;"))
            s.commit()
        return True
    except Exception as e:
        # Fallback para DELETE se TRUNCATE falhar (dependendo da permissão)
        try:
            with conn.session as s:
                s.execute(text("DELETE FROM notams;"))
                s.commit()
            return True
        except Exception as e2:
            st.error(f"Erro ao limpar tabela: {e2}")
            return False

# ... (Mantenha carregar_frota_monitorada, adicionar_icao, etc. iguais) ...
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
            s.execute(text("INSERT INTO frota_icao (icao, descricao) VALUES (:i, :d)"), params={"i": icao.upper().strip(), "d": desc})
            s.commit()
        return True
    except:
        return False

def remover_icao(icao):
    conn = get_connection()
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM frota_icao WHERE icao = :i"), params={"i": icao})
            s.commit()
        return True
    except:
        return False

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
                s.execute(text("INSERT INTO config_filtros (tipo, valor) VALUES (:t, :v)"), dados)
            s.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar filtros: {e}")
        return False