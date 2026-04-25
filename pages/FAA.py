import streamlit as st
import pandas as pd

# ==============================================================================
# FUNÇÃO DE TRATAMENTO DE DATAS
# ==============================================================================
def tratar_data_faa(data_str):
    """
    Converte as datas do formato americano (MM/DD/YYYY HHMM) para datetime.
    Trata casos de NOTAMs permanentes ou com término estimado.
    """
    if pd.isna(data_str):
        return None
    
    data_str = str(data_str).strip()
    
    # Tratamento para NOTAMs Permanentes (PERM)
    # Sugestão: jogar para o ano 2099 para facilitar buscas no Supabase "onde expiração > hoje"
    if data_str.upper() == 'PERM':
        return pd.Timestamp('2099-12-31 23:59:59')
    
    # Tratamento para datas estimadas (EST)
    if data_str.endswith('EST'):
        data_str = data_str.replace('EST', '').strip()
        
    try:
        # Converte de 'MM/DD/YYYY HHMM' para formato universal Ano-Mes-Dia Hora:Minuto
        return pd.to_datetime(data_str, format='%m/%d/%Y %H%M')
    except Exception as e:
        return None

# ==============================================================================
# FUNÇÃO PRINCIPAL DE LIMPEZA
# ==============================================================================
def limpar_planilha_notams(arquivo):
    # 0. Volta o ponteiro de leitura para o início (essencial no Streamlit)
    arquivo.seek(0)
    
    # 1. Pular as 4 primeiras linhas e usar configurações robustas
    df = pd.read_csv(
        arquivo, 
        skiprows=4, 
        encoding='latin1', 
        engine='python',         
        on_bad_lines='skip'      
    )
    
    # 2. LIMPEZA DOS TÍTULOS: Remove espaços invisíveis do começo e do fim dos nomes das colunas
    df.columns = df.columns.str.strip()
    
    # 3. Renomear as colunas
    colunas_map = {
        'Location': 'loc',
        'NOTAM #/LTA #': 'n', 
        'Class': 'classe',
        'Issue Date (UTC)': 'dt_emissao',
        'Effective Date (UTC)': 'dt_inicio',   
        'Expiration Date (UTC)': 'dt_fim',     
        'NOTAM Condition/LTA subject/Construction graphic title': 'texto_bruto' 
    }
    df = df.rename(columns=colunas_map)
    
    # --- SISTEMA DE ALERTA ---
    # Se a renomeação falhar, o app não quebra. Ele avisa você na tela!
    if 'loc' not in df.columns or 'n' not in df.columns:
        st.error("⚠️ As colunas esperadas não foram encontradas no arquivo.")
        st.warning("Veja abaixo as colunas que o Pandas conseguiu ler. Pode ser que o arquivo tenha mudado de formato (ou o skiprows=4 precise ser ajustado):")
        st.write(df.columns.tolist())
        st.stop() # Interrompe o código aqui para você poder ver a tela
    # -------------------------

    # 4. Remover linhas vazias
    df = df.dropna(subset=['loc', 'n'])
    
    # 5. Tratar as Datas
    df['dt_emissao'] = df['dt_emissao'].apply(tratar_data_faa)
    df['dt_inicio'] = df['dt_inicio'].apply(tratar_data_faa)
    df['dt_fim'] = df['dt_fim'].apply(tratar_data_faa)
    
    # 6. Limpezas de texto
    df['loc'] = df['loc'].astype(str).str.strip().str.upper()
    df['n'] = df['n'].astype(str).str.strip()
    df['classe'] = df['classe'].astype(str).str.strip()
    
    # 7. Cria uma coluna indicando que a data é permanente
    df['is_perm'] = df['dt_fim'] == pd.Timestamp('2099-12-31 23:59:59')

    return df

# ==============================================================================
# INTERFACE STREAMLIT PARA TESTE
# ==============================================================================
st.title("🗂️ Importador e Tratamento de NOTAMs")

arquivo_upload = st.file_uploader("Faça o upload do arquivo CSV/XLS da FAA", type=["csv", "xls", "xlsx"])

if arquivo_upload:
    with st.spinner("Processando e limpando dados..."):
        # Executa a limpeza
        df_tratado = limpar_planilha_notams(arquivo_upload)
        
        st.success(f"Arquivo processado com sucesso! {len(df_tratado)} registros encontrados.")
        
        # Exibe os dados prontos para o banco
        st.subheader("Visualização dos Dados Tratados")
        st.dataframe(df_tratado, use_container_width=True)
        
        # Próximos passos (Ainda não conectado)
        if st.button("Subir para o Supabase (Em Breve)", type="primary"):
            st.info("Aqui entrará o código da API do Supabase!")