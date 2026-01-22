import streamlit as st
import pandas as pd
from supabase import create_client, Client
from utils import parser_notam

st.set_page_config(page_title="Processamento Supabase", layout="wide")

st.title("📊 Processamento em Lote (Supabase)")
st.markdown("Busca NOTAMs com **Item D** preenchido, processa os horários e gera uma tabela analítica.")

# ==============================================================================
# 1. CONFIGURAÇÃO DA CONEXÃO
# ==============================================================================
with st.expander("⚙️ Configurações de Conexão", expanded=True):
    col1, col2 = st.columns(2)
    
    # Tenta pegar dos secrets do Streamlit primeiro, senão pede input
    # (Configure .streamlit/secrets.toml para não precisar digitar sempre)
    sb_url = st.text_input("Supabase URL", value=st.secrets.get("SUPABASE_URL", ""))
    sb_key = st.text_input("Supabase Key", value=st.secrets.get("SUPABASE_KEY", ""), type="password")
    
    table_name = st.text_input("Nome da Tabela", value="notams")
    
    # Mapeamento de Colunas (Caso seu banco tenha nomes diferentes)
    c1, c2, c3, c4 = st.columns(4)
    col_id = c1.text_input("Coluna ID/Código", value="notam_code")
    col_b  = c2.text_input("Coluna Início (B)", value="date_begin")
    col_c  = c3.text_input("Coluna Fim (C)", value="date_end")
    col_d  = c4.text_input("Coluna Texto (D)", value="item_d")

# ==============================================================================
# 2. O ALGORITMO
# ==============================================================================
def buscar_e_processar():
    if not sb_url or not sb_key:
        st.error("Preencha a URL e a KEY do Supabase.")
        return

    # 1. CONEXÃO
    try:
        supabase: Client = create_client(sb_url, sb_key)
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
        return

    # 2. EXTRAÇÃO (Query)
    with st.status("📡 Conectando ao Supabase...", expanded=True) as status:
        st.write("Buscando NOTAMs com Item D preenchido...")
        
        # Seleciona apenas as colunas necessárias para economizar banda
        # Filtra onde item_d NÃO é nulo e NÃO é vazio
        response = supabase.table(table_name)\
            .select(f"{col_id}, {col_b}, {col_c}, {col_d}")\
            .neq(col_d, "")\
            .neq(col_d, "None")\
            .execute()
        
        dados = response.data
        total_notams = len(dados)
        st.write(f"📦 {total_notams} NOTAMs encontrados para processamento.")
        
        if total_notams == 0:
            status.update(label="Nenhum dado encontrado.", state="error")
            return

        # 3. TRANSFORMAÇÃO (Parsing)
        st.write("🔄 Interpretando horários com o Parser V13...")
        
        tabela_final = []
        erros = 0
        
        progress_bar = st.progress(0)
        
        for i, row in enumerate(dados):
            # Atualiza barra de progresso
            progress_bar.progress((i + 1) / total_notams)
            
            try:
                raw_d = row.get(col_d, "")
                raw_b = row.get(col_b, "")
                raw_c = row.get(col_c, "")
                codigo = row.get(col_id, "N/A")
                
                # CHAMA O NOSSO PARSER BLINDADO
                slots = parser_notam.interpretar_periodo_atividade(raw_d, codigo, raw_b, raw_c)
                
                # EXPLOSÃO: Cria uma linha na tabela final para CADA slot gerado
                for slot in slots:
                    tabela_final.append({
                        "NOTAM Code": codigo,
                        "Início Real": slot['inicio'],
                        "Fim Real": slot['fim'],
                        "Duração (h)": (slot['fim'] - slot['inicio']).total_seconds() / 3600,
                        "Texto D": raw_d  # Opcional: manter o texto original para conferência
                    })
                    
            except Exception as e:
                erros += 1
                # Opcional: Logar o erro
        
        status.update(label="Processamento Concluído!", state="complete")

    # 4. EXIBIÇÃO E EXPORTAÇÃO
    if tabela_final:
        df = pd.DataFrame(tabela_final)
        
        # Formatações visuais
        df_show = df.copy()
        df_show['Início Real'] = df_show['Início Real'].dt.strftime('%d/%m/%Y %H:%M')
        df_show['Fim Real'] = df_show['Fim Real'].dt.strftime('%d/%m/%Y %H:%M')
        df_show['Duração (h)'] = df_show['Duração (h)'].round(2)

        st.success(f"✅ Sucesso! Gerados {len(df)} slots de atividade a partir de {total_notams} NOTAMs.")
        if erros > 0:
            st.warning(f"⚠️ {erros} NOTAMs tiveram problemas de leitura.")

        st.dataframe(df_show, use_container_width=True)
        
        # Botão de Download Excel
        # Requer: pip install openpyxl
        try:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Slots')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Baixar Relatório em Excel",
                data=excel_data,
                file_name="relatorio_slots_notams.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except ImportError:
            st.warning("Instale 'xlsxwriter' ou 'openpyxl' para habilitar o download em Excel.")
            st.code("pip install xlsxwriter")

# ==============================================================================
# 3. INTERFACE
# ==============================================================================
if st.button("🚀 Carregar e Processar", type="primary"):
    buscar_e_processar()