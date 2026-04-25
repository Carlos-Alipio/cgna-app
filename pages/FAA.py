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
    # 1. Pular as 4 primeiras linhas e usar configurações robustas
    df = pd.read_csv(
        arquivo, 
        skiprows=4, 
        encoding='latin1', 
        engine='python',         # Usa o motor Python (mais inteligente para lidar com textos complexos e quebras de linha)
        on_bad_lines='skip'      # Se alguma linha vier totalmente quebrada, ele ignora a linha e salva o resto, sem travar o app
    )
    
    # 2. Renomear as colunas para o padrão do Banco de Dados (snake_case)
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
    
    # 3. Remover linhas vazias caso o CSV tenha sujeira no final
    df = df.dropna(subset=['loc', 'n'])
    
    # 4. Tratar as Datas
    df['dt_emissao'] = df['dt_emissao'].apply(tratar_data_faa)
    df['dt_inicio'] = df['dt_inicio'].apply(tratar_data_faa)
    df['dt_fim'] = df['dt_fim'].apply(tratar_data_faa)
    
    # 5. Limpezas de texto
    df['loc'] = df['loc'].str.strip().str.upper()
    df['n'] = df['n'].str.strip()
    df['classe'] = df['classe'].str.strip()
    
    # Cria uma coluna indicando que a data é permanente (caso queira no Supabase)
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