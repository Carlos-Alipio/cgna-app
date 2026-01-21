import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta

# --- CONEXÃO ---
def get_connection():
    return st.connection("supabase", type="sql")

# --- GERENCIAMENTO DE NOTAMS ---
def salvar_notams(df):
    conn = get_connection()
    
    # ==============================================================================
    # 🛠️ HOOK DE CORREÇÃO: TRATAMENTO DE 'PERM' vindo do CSV
    # ==============================================================================
    try:
        # 1. Normalização de Nomes de Colunas
        # O CSV pode vir como "Data Inicial"/"Data Final" ou "b"/"c". Vamos padronizar.
        mapa_colunas = {
            'Data Inicial': 'b',
            'Data Final': 'c',
            'Texto': 'd',
            'Localidade': 'loc',
            'NOTAM': 'n'
        }
        df = df.rename(columns=mapa_colunas)

        # 2. Conversão da Data de Início (b)
        df['b_dt'] = pd.to_datetime(df['b'], errors='coerce')
        
        # 3. Função de Correção Linha a Linha
        def corrigir_data_fim(row):
            # Pega valores brutos como string maiúscula
            val_c = str(row.get('c', '')).upper().strip()
            texto_d = str(row.get('d', '')).upper().strip()
            dt_inicio = row['b_dt']
            
            # Se não tem data de início válida, retorna o que veio
            if pd.isna(dt_inicio):
                return row.get('c')
            
            # --- VERIFICAÇÃO DE PERM ---
            # A. Está escrito "PERM" na coluna de Data Final?
            is_perm_c = "PERM" in val_c
            
            # B. Está escrito REF AIP ou PERM no Texto? (Backup)
            gatilhos = ["REF: AIP", "REF AIP", "AD 2", "PERM", "AIP AD"]
            is_perm_text = any(g in texto_d for g in gatilhos)
            
            # SE FOR PERMANENTE:
            if is_perm_c or is_perm_text:
                # Calcula Data Início + 365 dias
                nova_data = dt_inicio + timedelta(days=365)
                return nova_data
            
            # SE NÃO FOR PERM:
            # Tenta aproveitar a data que veio, se for válida
            try:
                # Se for formato ISO ou BR, o pandas resolve depois, retornamos o valor original
                # Mas se o valor for vazio ou inválido, precisamos cuidar
                if len(val_c) < 6: # String muito curta, provavelmente erro
                    return row.get('c')
                return row.get('c')
            except:
                return row.get('c')

        # 4. Aplica a correção
        if 'b' in df.columns and 'c' in df.columns:
            df['c'] = df.apply(corrigir_data_fim, axis=1)
        
        # Remove coluna auxiliar
        if 'b_dt' in df.columns:
            df = df.drop(columns=['b_dt'])

    except Exception as e:
        print(f"Aviso no tratamento de datas: {e}")
    
    # ==============================================================================

    try:
        with conn.session as s:
            with st.spinner(f"💾 Salvando {len(df)} registros no banco de dados..."):
                # Garante que as colunas essenciais existam antes de salvar
                cols_banco = ['loc', 'n', 'b', 'c', 'd'] # Adicione outras se necessário
                # Filtra apenas colunas que existem no DF para não dar erro
                cols_salvar = [c for c in cols_banco if c in df.columns]
                
                # Se houver outras colunas no DF (como Assunto, Condição), mantém também
                # A estratégia 'replace' recria a tabela com as colunas do DF
                
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

# ... (Mantenha as demais funções carregar_notams, carregar_frota, etc. inalteradas) ...
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