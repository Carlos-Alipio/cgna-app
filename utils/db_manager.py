import streamlit as st
import pandas as pd
from sqlalchemy import text

# Conexão centralizada
def get_connection():
    return st.connection("supabase", type="sql")

def salvar_notams(df):
    conn = get_connection()
    try:
        # Abre a sessão
        with conn.session as s:
            # Dica de Performance:
            # 1. method='multi': Envia várias linhas em um único comando SQL (muito mais rápido)
            # 2. chunksize=500: Envia de 500 em 500 para não travar a memória
            
            with st.spinner(f"💾 Salvando {len(df)} registros no banco de dados..."):
                df.to_sql(
                    'notams', 
                    conn.engine, 
                    if_exists='replace', 
                    index=False, 
                    chunksize=500, # Tamanho ideal para internet comum
                    method='multi' # Turbo mode para SQL
                )
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Banco: {e}")
        return False

def carregar_notams():
    conn = get_connection()
    try:
        # ttl=0 garante que não pegue cache velho
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
    
# ... (código existente) ...

# --- NOVAS FUNÇÕES PARA FILTROS CRÍTICOS ---

def carregar_filtros_configurados():
    """Retorna um DataFrame com todos os filtros salvos"""
    conn = get_connection()
    try:
        return conn.query("SELECT * FROM config_filtros", ttl=0)
    except:
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