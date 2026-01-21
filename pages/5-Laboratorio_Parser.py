import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timedelta
from utils import parser_notam

st.set_page_config(page_title="Lab Parser Item D", layout="wide")
st.title("🛠️ Laboratório de Testes: Parser NOTAM")
st.markdown("Ferramenta para validação e auditoria visual do algoritmo de interpretação.")

tab_manual, tab_lote = st.tabs(["🧪 Teste Manual", "📦 Auditoria em Lote (API)"])

# ==============================================================================
# ABA 1: TESTE MANUAL
# ==============================================================================
with tab_manual:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("1. Contexto")
        dt_hoje = datetime.now()
        dt_b = st.date_input("Início (Item B)", value=dt_hoje)
        dt_c = st.date_input("Fim (Item C)", value=dt_hoje + timedelta(days=60))
        str_b = dt_b.strftime("%y%m%d") + "0000"
        str_c = dt_c.strftime("%y%m%d") + "2359"
        st.caption(f"Vigência: {dt_b.strftime('%d/%m/%Y')} a {dt_c.strftime('%d/%m/%Y')}")

    with c2:
        st.subheader("2. Texto (Item D)")
        exemplos = {
            "Padrão Diário": "DLY 0600-1200",
            "Dias da Semana": "MON TIL FRI 1000/1600",
            "Exceção Fim de Semana": "DLY 0800-1700 EXC SAT SUN",
            "Livre para digitar": ""
        }
        escolha = st.selectbox("Modelos:", list(exemplos.keys()))
        texto_padrao = exemplos[escolha] if escolha != "Livre para digitar" else ""
        item_d_input = st.text_area("Digite o Item D:", value=texto_padrao, height=100)

    if st.button("🔬 Analisar Manualmente", type="primary"):
        if not item_d_input:
            st.warning("Digite algo.")
            st.stop()
        try:
            res = parser_notam.interpretar_periodo_atividade(item_d_input, "SBGR", str_b, str_c)
            if not res:
                st.error("❌ Parser não identificou padrões.")
            else:
                df_res = pd.DataFrame(res)
                df_res['Dia'] = df_res['inicio'].dt.strftime('%d/%m/%Y (%a)')
                df_res['Hora'] = df_res['inicio'].dt.strftime('%H:%M') + " - " + df_res['fim'].dt.strftime('%H:%M')
                st.success(f"✅ Identificados {len(df_res)} períodos.")
                st.dataframe(df_res[['Dia', 'Hora']], use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")

# ==============================================================================
# ABA 2: TESTE EM LOTE (AUDITORIA REAL)
# ==============================================================================
with tab_lote:
    st.subheader("🤖 Auditoria de Parser (Brasil)")
    
    col_conf1, col_conf2 = st.columns([3, 1])
    with col_conf1:
        brasil_todo = st.checkbox("🌍 Analisar BRASIL INTEIRO (5 FIRs)", value=True)
        if not brasil_todo:
            icaos_teste = st.text_input("Filtrar Localidades:", value="SBGR, SBGL, SBSP, SBBR")
    with col_conf2:
        st.write("")
        btn_iniciar = st.button("🚀 Iniciar Auditoria", type="primary")

    # Credenciais e URL
    API_URL = "http://aisweb.decea.mil.br/api/" # Ajustado conforme seu snippet
    API_KEY = "1279934730"
    API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"

    if btn_iniciar:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # Define os códigos de consulta
        if brasil_todo:
            # As 5 FIRs do Brasil via icaocode
            icaos_consulta = "SBAZ,SBBS,SBCW,SBRE,SBAO"
            msg_busca = "Baixando dados completos das 5 FIRs (Isso pode levar alguns segundos)..."
        else:
            icaos_consulta = icaos_teste.replace(" ", "")
            msg_busca = f"Baixando dados de: {icaos_consulta}..."

        status_text.info(f"📡 {msg_busca}")
        
        todos_items_xml = []
        
        try:
            # Chamada Única e Robusta
            params = {
                'apiKey': API_KEY, 
                'apiPass': API_PASS, 
                'area': 'notam', 
                'icaocode': icaos_consulta
            }
            
            # Timeout de 60s para garantir o download das FIRs
            response = requests.get(API_URL, params=params, timeout=60)
            
            if response.status_code == 200:
                try:
                    root = ET.fromstring(response.content)
                    todos_items_xml = root.findall("notam")
                except ET.ParseError:
                    st.error("Erro ao processar o XML retornado (arquivo corrompido ou incompleto).")
                    st.stop()
            else:
                st.error(f"Erro na API DECEA: {response.status_code}")
                st.stop()
                
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            st.stop()

        total_items = len(todos_items_xml)
        if total_items == 0:
            st.warning("Nenhum dado encontrado.")
            st.stop()

        status_text.info(f"Processando {total_items} NOTAMs...")
        resultados_lote = []

        # Helper Data API (YYYY-MM-DD HH:MM:SS -> YYMMDDHHMM)
        def fmt_api_date(d_str):
            if not d_str: return "2501010000"
            try: return datetime.strptime(d_str, "%Y-%m-%d %H:%M:%S").strftime("%y%m%d%H%M")
            except: return "2501010000"

        # Helper Extração Segura XML
        def safe_get(item, tag):
            f = item.find(tag)
            return f.text if f is not None and f.text else ""

        # LOOP DE ANÁLISE
        for i, item in enumerate(todos_items_xml):
            if i % (total_items // 20 + 1) == 0: 
                progress_bar.progress((i + 1) / total_items)
            
            notam_id = safe_get(item, "notam_id")
            loc = safe_get(item, "loc")
            dt_ini = safe_get(item, "dt_ini")
            dt_fim = safe_get(item, "dt_fim")
            texto = safe_get(item, "texto")
            
            # Extrai Item D (Regex procura D) até E) ou fim)
            match_d = re.search(r'(?:^|\s)D\)\s*(.*?)(?=\s*[E-G]\)|\s*$)', texto, re.DOTALL)
            item_d = match_d.group(1).strip() if match_d else None
            
            status = "N/A"
            res_parser_str = "-"
            
            if item_d:
                if item_d.upper() in ["NIL", "NONE", ""]:
                    status = "IGNORADO (NIL)"
                else:
                    try:
                        res = parser_notam.interpretar_periodo_atividade(
                            item_d, loc, fmt_api_date(dt_ini), fmt_api_date(dt_fim)
                        )
                        if res:
                            status = "SUCESSO"
                            res_parser_str = f"{len(res)} dias gerados"
                        else:
                            status = "FALHA"
                    except:
                        status = "ERRO CÓDIGO"
            else:
                status = "SEM ITEM D"

            resultados_lote.append({
                "LOC": loc,
                "NOTAM": notam_id,
                "Início (B)": dt_ini,
                "Fim (C)": dt_fim,
                "Item D (Texto Analisado)": item_d if item_d else "-",
                "Status": status,
                "Parser Output": res_parser_str
            })

        progress_bar.progress(100)
        status_text.success("Concluído!")
        
        # EXIBIÇÃO VISUAL
        df = pd.DataFrame(resultados_lote)
        
        st.divider()
        st.markdown("### 🕵️ Auditoria Visual")
        
        # Filtros
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            filtro_status = st.radio(
                "Visualizar:", 
                ["🚨 Apenas Falhas", "✅ Sucessos", "📄 Tudo"],
                horizontal=True
            )
        
        # Filtragem do DataFrame
        if filtro_status == "🚨 Apenas Falhas":
            df_show = df[df['Status'].isin(["FALHA", "ERRO CÓDIGO"])]
            msg_qtd = f"{len(df_show)} falhas encontradas."
            tipo_msg = st.error
        elif filtro_status == "✅ Sucessos":
            df_show = df[df['Status'] == "SUCESSO"]
            msg_qtd = f"{len(df_show)} sucessos."
            tipo_msg = st.success
        else:
            df_show = df
            msg_qtd = f"{len(df_show)} registros totais."
            tipo_msg = st.info

        tipo_msg(msg_qtd)

        # Remove duplicatas de texto para facilitar leitura (apenas na view)
        if filtro_status == "🚨 Apenas Falhas" and not df_show.empty:
             if st.checkbox("Agrupar falhas idênticas (Remover Duplicatas)", value=True):
                 df_show = df_show.drop_duplicates(subset=['Item D (Texto Analisado)'])

        # Tabela Rica
        st.dataframe(
            df_show,
            use_container_width=True,
            column_config={
                "Item D (Texto Analisado)": st.column_config.TextColumn("Item D", width="large"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Início (B)": st.column_config.TextColumn("Início", width="medium"),
                "Fim (C)": st.column_config.TextColumn("Fim", width="medium"),
            },
            height=600
        )