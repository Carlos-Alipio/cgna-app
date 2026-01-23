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
    # 🛠️ HOOK DE CORREÇÃO: TRATAMENTO INTELIGENTE DE DATAS E PERM
    # ==============================================================================
    try:
        # 1. Normalização de Nomes de Colunas (CSV -> Padrão Interno)
        mapa_colunas = {
            'Data Inicial': 'b',
            'Data Final': 'c',
            'Texto': 'd',
            'Localidade': 'loc',
            'NOTAM': 'n'
        }
        df = df.rename(columns=mapa_colunas)

        # 2. Garante que a Data de Início (b) seja datetime para cálculos
        df['b_dt'] = pd.to_datetime(df['b'], errors='coerce')
        
        # 3. Função de Correção Linha a Linha
        def corrigir_data_fim(row):
            # Pega valores brutos como string maiúscula para análise
            val_c = str(row.get('c', '')).upper().strip()
            texto_d = str(row.get('d', '')).upper().strip()
            dt_inicio = row['b_dt']
            
            # Se não tem data de início válida, retorna o que veio (não dá pra calcular)
            if pd.isna(dt_inicio):
                return row.get('c')
            
            # --- VERIFICAÇÃO 1: "PERM" EXPLÍCITO NO CAMPO C ---
            # (Resolve o caso do XML que você mandou)
            tem_perm_em_c = "PERM" in val_c
            
            # --- VERIFICAÇÃO 2: CONTEXTO DE INFRAESTRUTURA NO TEXTO D ---
            # (Resolve casos onde o sistema trocou PERM por data curta de 30 dias)
            gatilhos_texto = [
                "REF: AIP", "REF AIP", "AD 2", "AIP AD", 
                "PERM", "PERMANENTE", "DEFINITIVO",
                "RESA", "AUSENCIA DE RESA", # Obras longas
                "OBST", "OBSTACLE",         # Obstáculos são fixos
                "INSTL", "INSTALADO"
            ]
            tem_perm_no_texto = any(g in texto_d for g in gatilhos_texto)
            
            # REGRA FINAL: Se for PERM por C ou por Texto -> Início + 365 dias
            if tem_perm_em_c or tem_perm_no_texto:
                return dt_inicio + timedelta(days=365)
            
            # SE NÃO FOR PERM: Tenta manter a data original
            return row.get('c')

        # 4. Aplica a correção na coluna 'c'
        if set(['b', 'c']).issubset(df.columns):
            df['c'] = df.apply(corrigir_data_fim, axis=1)
        
        # Remove coluna auxiliar temporária
        if 'b_dt' in df.columns:
            df = df.drop(columns=['b_dt'])

    except Exception as e:
        print(f"Aviso no tratamento de datas: {e}")
    
    # ==============================================================================

    try:
        with conn.session as s:
            with st.spinner(f"💾 Salvando {len(df)} registros no banco de dados..."):
                # Garante que salvamos apenas colunas úteis para não dar erro de schema
                # (Adapte esta lista se seu banco tiver mais colunas)
                cols_banco = ['loc', 'n', 'b', 'c', 'd', 'e', 'tp', 'status', 'cat'] 
                
                # Filtra colunas do DF que existem na lista acima (case insensitive match se necessário)
                # Aqui simplificado para salvar tudo que o DF tem, pois 'replace' recria a tabela
                
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

# --- FUNÇÃO DE LIMPEZA (Útil para resetar antes de carga total) ---
def limpar_tabela_notams():
    """Apaga todos os registros da tabela NOTAMS"""
    conn = get_connection()
    try:
        with conn.session as s:
            # Tenta TRUNCATE (mais rápido)
            try:
                s.execute(text("TRUNCATE TABLE notams;"))
            except:
                # Fallback para DELETE
                s.execute(text("DELETE FROM notams;"))
            s.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao limpar tabela: {e}")
        return False

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

# --- GERENCIAMENTO DE FILTROS ---
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
    
# No arquivo utils/db_manager.py

def salvar_slots_manuais(notam_id, dados_json):
    """
    Salva a lista de slots para um NOTAM específico.
    Sugestão: Usar uma tabela 'notam_obras_slots' com colunas: id, notam_id, dados (jsonb)
    """
    # Exemplo Supabase:
    # supabase.table('notam_obras_slots').upsert({'notam_id': notam_id, 'dados': dados_json}).execute()
    pass

def carregar_slots_manuais(notam_id):
    """Retorna a lista de slots salvos para aquele NOTAM"""
    # Exemplo:
    # response = supabase.table('notam_obras_slots').select('dados').eq('notam_id', notam_id).execute()
    # return response.data[0]['dados'] if response.data else []
    return []

def limpar_registros_orfaos(lista_ids_ativos):
    """
    Deleta registros da tabela manual que não estão na lista de IDs ativos.
    Isso atende ao requisito: 'quando notams saírem, o cadastro deve ser deletado'.
    """
    # Exemplo SQL: DELETE FROM notam_obras_slots WHERE notam_id NOT IN (lista_ids_ativos)
    pass

import json
import os
import pandas as pd
from datetime import datetime

# Arquivo onde os dados serão salvos
DB_FILE = "slots_db.json"

def _load_db():
    """Função interna para ler o JSON do disco"""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao ler banco: {e}")
        return {}

def _save_db(data):
    """Função interna para salvar o JSON no disco"""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar banco: {e}")

# --- FUNÇÕES PÚBLICAS (As que o app usa) ---

def salvar_slots_manuais(notam_id, slots_lista):
    """
    Salva a lista de slots para um ID de NOTAM específico.
    Sobrescreve o que existia antes para aquele NOTAM.
    """
    db = _load_db()
    db[notam_id] = slots_lista
    _save_db(db)

def carregar_slots_manuais(notam_id):
    """
    Retorna a lista de slots salva. Se não existir, retorna lista vazia.
    """
    db = _load_db()
    return db.get(notam_id, [])

def limpar_registros_orfaos(ids_ativos):
    """
    Remove do banco os agendamentos de NOTAMs que não existem mais na lista ativa.
    """
    db = _load_db()
    
    # Identifica IDs no banco que não estão na lista de ativos
    ids_no_banco = list(db.keys())
    alterou = False
    
    for n_id in ids_no_banco:
        if n_id not in ids_ativos:
            del db[n_id]
            alterou = True
            print(f"🧹 Limpeza: Removidos dados do NOTAM órfão {n_id}")
    
    if alterou:
        _save_db(db)

# ... (Mantenha suas outras funções de carregar_notams aqui) ...