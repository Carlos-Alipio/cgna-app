import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from utils import parser_notam

st.set_page_config(page_title="Lab Parser Item D", layout="wide")
st.title("🛠️ Laboratório de Testes: Parser NOTAM")
st.markdown("""
Esta ferramenta serve para **estressar** o algoritmo de interpretação de horários (Item D).
Teste textos complexos aqui para verificar se o robô está calculando os dias e horas corretamente.
""")

st.divider()

# ==============================================================================
# 1. PARÂMETROS DE ENTRADA
# ==============================================================================
c1, c2 = st.columns([1, 2])

with c1:
    st.subheader("1. Contexto do NOTAM")
    # Datas fictícias do item B e C para dar contexto ao parser
    dt_hoje = datetime.now()
    dt_b = st.date_input("Início (Item B)", value=dt_hoje)
    dt_c = st.date_input("Fim (Item C)", value=dt_hoje + timedelta(days=60))
    
    # Monta strings no formato YYMMDDHHMM (padrão NOTAM)
    str_b = dt_b.strftime("%y%m%d") + "0000"
    str_c = dt_c.strftime("%y%m%d") + "2359"
    
    st.caption(f"Simulando vigência: {dt_b.strftime('%d/%m/%Y')} até {dt_c.strftime('%d/%m/%Y')}")

with c2:
    st.subheader("2. Texto para Teste (Item D)")
    
    # Exemplos prontos para facilitar
    exemplos = {
        "Padrão Diário": "DLY 0600-1200",
        "Dias da Semana": "MON TIL FRI 1000/1600",
        "Exceção Fim de Semana": "DLY 0800-1700 EXC SAT SUN",
        "Nascer ao Pôr do Sol": "DLY SR-SS",
        "Datas Específicas": "SEP 05 08 12 20 2200-0200",
        "Madrugada (Dia seguinte)": "DLY 2200-0500",
        "Múltiplos Horários": "MON WED FRI 1000-1200 AND 1400-1600",
        "Livre para digitar": ""
    }
    
    escolha = st.selectbox("Escolha um padrão ou digite:", list(exemplos.keys()))
    
    texto_padrao = exemplos[escolha] if escolha != "Livre para digitar" else ""
    item_d_input = st.text_area("Digite o texto do Item D:", value=texto_padrao, height=100)

# ==============================================================================
# 2. PROCESSAMENTO E RESULTADO
# ==============================================================================
st.divider()

if st.button("🔬 Analisar Texto", type="primary"):
    if not item_d_input:
        st.warning("Digite algo no Item D.")
        st.stop()

    st.subheader("3. Resultado da Interpretação")
    
    try:
        # CHAMA O SEU PARSER REAL
        # Usamos um ICAO genérico (SBGR) para cálculo de sol se necessário
        resultado = parser_notam.interpretar_periodo_atividade(
            item_d_input, 
            "SBGR", 
            str_b, 
            str_c
        )
        
        if not resultado:
            st.error("❌ O parser não conseguiu identificar nenhum padrão de data/hora.")
        else:
            # Transforma em DataFrame para visualizar
            df_res = pd.DataFrame(resultado)
            
            # Formata para leitura humana
            df_res['Dia da Semana'] = df_res['inicio'].dt.strftime('%A')
            df_res['Data Início'] = df_res['inicio'].dt.strftime('%d/%m/%Y')
            df_res['Hora Início'] = df_res['inicio'].dt.strftime('%H:%M')
            df_res['Data Fim'] = df_res['fim'].dt.strftime('%d/%m/%Y')
            df_res['Hora Fim'] = df_res['fim'].dt.strftime('%H:%M')
            
            # Calcula duração
            def calc_duracao(row):
                delta = row['fim'] - row['inicio']
                total_min = int(delta.total_seconds() / 60)
                h = total_min // 60
                m = total_min % 60
                return f"{h:02d}h {m:02d}m"

            df_res['Duração'] = df_res.apply(calc_duracao, axis=1)

            # Métricas
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Dias Encontrados", len(df_res))
            col_m1.success("✅ Sucesso")
            
            # Visualização Gráfica
            st.dataframe(
                df_res[['Dia da Semana', 'Data Início', 'Hora Início', 'Data Fim', 'Hora Fim', 'Duração']],
                use_container_width=True, 
                height=400
            )

            # Validação Visual (JSON Bruto)
            with st.expander("Ver dados brutos (JSON)"):
                st.write(resultado)

    except Exception as e:
        st.error(f"💥 Erro fatal no código do parser: {e}")
        st.exception(e)