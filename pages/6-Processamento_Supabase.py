import streamlit as st
import pandas as pd
from utils import parser_notam
# Importe aqui o arquivo onde você guardou a função get_connection
# Exemplo: se estiver em utils/db_connection.py
from utils.db_manager import get_connection 

st.set_page_config(page_title="Processamento Supabase", layout="wide")

st.title("📊 Processamento em Lote (Via SQL)")
st.markdown("Busca no Banco de Dados todos os NOTAMs com **Item D** preenchido e processa os horários.")

# ==============================================================================
# 1. ALGORITMO DE BUSCA E PROCESSAMENTO
# ==============================================================================
def processar_banco_dados():
    # 1. CONEXÃO E QUERY
    conn = get_connection()
    
    with st.status("📡 Acessando Banco de Dados...", expanded=True) as status:
        st.write("Executando Query SQL...")
        
        # Seleciona apenas as colunas essenciais
        # Filtra onde 'd' não é nulo e não é vazio
        # Ajuste os nomes das colunas conforme sua tabela (n, b, c, d)
        try:
            df_db = conn.query(
                "SELECT n, b, c, d FROM notams WHERE d IS NOT NULL AND d <> ''", 
                ttl=0
            )
        except Exception as e:
            st.error(f"Erro na Query: {e}")
            status.update(label="Falha na conexão", state="error")
            return

        total_notams = len(df_db)
        st.write(f"📦 {total_notams} NOTAMs encontrados com Item D.")
        
        if total_notams == 0:
            status.update(label="Nenhum dado encontrado.", state="error")
            return

        # 2. TRANSFORMAÇÃO (Parsing)
        st.write("🔄 Interpretando horários com Parser V13...")
        
        tabela_final = []
        erros = 0
        
        progress_bar = st.progress(0)
        
        # Itera sobre o DataFrame do Pandas retornado pelo SQL
        for index, row in df_db.iterrows():
            # Atualiza barra de progresso
            progress_bar.progress((index + 1) / total_notams)
            
            try:
                # Mapeamento das colunas do seu banco
                codigo = str(row['n'])
                raw_b = str(row['b'])
                raw_c = str(row['c'])
                raw_d = str(row['d'])
                
                # CHAMA O NOSSO PARSER BLINDADO
                # O parser vai ler o Item D e gerar N slots
                slots = parser_notam.interpretar_periodo_atividade(raw_d, codigo, raw_b, raw_c)
                
                # EXPLOSÃO: Cria uma linha na tabela final para CADA slot gerado
                for slot in slots:
                    tabela_final.append({
                        "NOTAM": codigo,
                        "Início Real": slot['inicio'],
                        "Fim Real": slot['fim'],
                        "Duração (h)": (slot['fim'] - slot['inicio']).total_seconds() / 3600,
                        "Item D Original": raw_d
                    })
                    
            except Exception as e:
                erros += 1
                # print(f"Erro no NOTAM {row.get('n')}: {e}")
        
        status.update(label="Processamento Concluído!", state="complete")

    # 3. EXIBIÇÃO E EXPORTAÇÃO
    if tabela_final:
        df_resultado = pd.DataFrame(tabela_final)
        
        # Formatações visuais para exibir na tela
        df_show = df_resultado.copy()
        df_show['Início Real'] = df_show['Início Real'].dt.strftime('%d/%m/%Y %H:%M')
        df_show['Fim Real'] = df_show['Fim Real'].dt.strftime('%d/%m/%Y %H:%M')
        df_show['Duração (h)'] = df_show['Duração (h)'].round(2)

        st.success(f"✅ Sucesso! Gerados {len(df_resultado)} slots de atividade a partir de {total_notams} NOTAMs.")
        
        if erros > 0:
            st.warning(f"⚠️ {erros} NOTAMs não puderam ser processados por erro de formatação.")

        # Exibe a tabela
        st.dataframe(df_show, use_container_width=True)
        
        # Botão de Download Excel
        try:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_resultado.to_excel(writer, index=False, sheet_name='Slots Detalhados')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Baixar Relatório Completo (Excel)",
                data=excel_data,
                file_name="relatorio_slots_notams.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except ImportError:
            st.error("Biblioteca 'xlsxwriter' não instalada. Adicione ao requirements.txt para baixar Excel.")

# ==============================================================================
# 2. INTERFACE
# ==============================================================================

st.info("Esta ferramenta lê diretamente da tabela `notams` do seu banco de dados.")

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🚀 Processar Agora", type="primary"):
        processar_banco_dados()