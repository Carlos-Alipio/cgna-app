import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parser_notam

st.set_page_config(page_title="Lab Parser Incremental", layout="wide")

st.title("🛠️ Laboratório de Parser (Desenvolvimento Incremental)")
st.markdown("""
Use esta ferramenta para validar o **Caso Atual**. 
Se o resultado estiver correto, passaremos para o próximo caso e adicionaremos este à lista de regressão.
""")

# --- ÁREA DE INPUT ---
st.subheader("1. Entrada de Dados (Caso Atual)")

c1, c2, c3 = st.columns(3)

with c1:
    # Inputs amigáveis para data/hora
    dt_inicio = st.date_input("Data Início (B)", value=datetime(2026, 1, 26))
    hr_inicio = st.time_input("Hora Início (B)", value=datetime.strptime("03:20", "%H:%M").time())
    
with c2:
    dt_fim = st.date_input("Data Fim (C)", value=datetime(2026, 2, 13))
    hr_fim = st.time_input("Hora Fim (C)", value=datetime.strptime("07:50", "%H:%M").time())

with c3:
    # Formata para o padrão RAW que o parser espera (YYMMDDHHMM)
    # Isso simula exatamente como os dados vêm do banco/api
    raw_b = datetime.combine(dt_inicio, hr_inicio).strftime("%y%m%d%H%M")
    raw_c = datetime.combine(dt_fim, hr_fim).strftime("%y%m%d%H%M")
    
    st.info(f"**String B simulada:** `{raw_b}`")
    st.info(f"**String C simulada:** `{raw_c}`")

# Texto D
st.markdown("---")
texto_d = st.text_area("Texto do Item D:", value="DLY 0320-0750", height=100)

# --- BOTÃO DE AÇÃO ---
if st.button("🔬 Processar NOTAM", type="primary"):
    
    # Chama o parser V1
    try:
        slots = parser_notam.interpretar_periodo_atividade(
            item_d_text=texto_d,
            icao="TESTE",
            item_b_raw=raw_b,
            item_c_raw=raw_c
        )
        
        # --- EXIBIÇÃO DOS RESULTADOS ---
        if not slots:
            st.warning("⚠️ O parser não retornou nenhum slot (Lista Vazia).")
        else:
            df = pd.DataFrame(slots)
            
            # Formatação para facilitar a leitura humana
            df['Dia Semana'] = df['inicio'].dt.strftime('%a').str.upper()
            df['Data Início'] = df['inicio'].dt.strftime('%d/%m/%Y')
            df['Hora Início'] = df['inicio'].dt.strftime('%H:%M')
            df['Data Fim'] = df['fim'].dt.strftime('%d/%m/%Y')
            df['Hora Fim'] = df['fim'].dt.strftime('%H:%M')
            
            # Cálculo de Duração
            df['Duração'] = df['fim'] - df['inicio']
            
            # Métricas
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Total de Slots Gerados", len(df))
            col_m2.metric("Duração do 1º Slot", str(df['Duração'].iloc[0]))

            st.markdown("### 📊 Detalhamento dos Slots")
            st.dataframe(
                df[['Dia Semana', 'Data Início', 'Hora Início', 'Data Fim', 'Hora Fim', 'Duração']],
                use_container_width=True,
                height=400
            )
            
    except Exception as e:
        st.error(f"💥 Erro Fatal no Parser: {str(e)}")