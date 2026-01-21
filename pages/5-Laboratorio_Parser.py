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
# ABA 2: TESTE EM LOTE (AUDITORIA)
# ==============================================================================
with tab_lote:
    st.subheader("🤖 Auditoria de Parser (Brasil)")
    
    col_conf1, col_conf2 = st.columns([3, 1])
    with col_conf1:
        brasil_todo = st.checkbox("🌍 Analisar BRASIL INTEIRO (Todas as FIRs)", value=True)
        if not brasil_todo:
            icaos_teste = st.text_input("Filtrar Localidades:", value="SBGR, SBGL, SBSP, SBBR")
    with col_conf2:
        st.write("")
        btn_iniciar = st.button("🚀 Iniciar Auditoria", type="primary")

    API_URL = "https://aisweb.decea.mil.br/api/"
    API_KEY = "1279934730"
    API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"

    if btn_iniciar:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        lista_urls = []
        if brasil_todo:
            firs = ['SBBS', 'SBCW', 'SBRE', 'SBAZ', 'SBAO']
            for fir in firs:
                lista_urls.append(f"{API_URL}?apiKey={API_KEY}&apiPass={API_PASS}&area=notam&fir={fir}")
        else:
            locais = icaos_teste.replace(" ", "")
            lista_urls.append(f"{API_URL}?apiKey={API_KEY}&apiPass={API_PASS}&area=notam&icaocode={locais}")
        
        todos_items_xml = []
        
        # 1. DOWNLOAD
        for idx, url in enumerate(lista_urls):
            status_text.info(f"Baixando dados... ({idx+1}/{len(lista_urls)})")
            try:
                r = requests.get(url, timeout=30)
                if r.status_code == 200:
                    root = ET.fromstring(r.content)
                    todos_items_xml.extend(root.findall("notam"))
            except: pass

        total_items = len(todos_items_xml)
        if total_items == 0:
            st.warning("Nenhum dado encontrado.")
            st.stop()

        status_text.info(f"Analisando {total_items} NOTAMs...")
        resultados_lote = []

        def fmt_api_date(d_str):
            if not d_str: return "2501010000"
            try: return datetime.strptime(d_str, "%Y-%m-%d %H:%M:%S").strftime("%y%m%d%H%M")
            except: return "2501010000"

        def safe_get(item, tag):
            f = item.find(tag)
            return f.text if f is not None and f.text else ""

        # 2. ANÁLISE
        for i, item in enumerate(todos_items_xml):
            if i % (total_items // 20 + 1) == 0: progress_bar.progress((i + 1) / total_items)
            
            notam_id = safe_get(item, "notam_id")
            loc = safe_get(item, "loc")
            dt_ini = safe_get(item, "dt_ini")
            dt_fim = safe_get(item, "dt_fim")
            texto = safe_get(item, "texto")
            
            # Extrai Item D
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
                            # Mostra resumo do que foi entendido (Qtd dias)
                            res_parser_str = f"{len(res)} dias calculados"
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
        
        # 3. EXIBIÇÃO VISUAL
        df = pd.DataFrame(resultados_lote)
        
        st.divider()
        st.markdown("### 🕵️ Auditoria Visual")
        
        # Filtros
        filtro_status = st.radio(
            "O que você quer ver?", 
            ["🚨 Apenas Falhas", "✅ Sucessos", "📄 Tudo"],
            horizontal=True
        )
        
        if filtro_status == "🚨 Apenas Falhas":
            df_show = df[df['Status'].isin(["FALHA", "ERRO CÓDIGO"])]
            st.error(f"Mostrando {len(df_show)} falhas de interpretação.")
        elif filtro_status == "✅ Sucessos":
            df_show = df[df['Status'] == "SUCESSO"]
            st.success(f"Mostrando {len(df_show)} NOTAMs interpretados corretamente.")
        else:
            df_show = df
            st.info(f"Mostrando todos os {len(df_show)} registros.")

        # Tabela Rica
        st.dataframe(
            df_show,
            use_container_width=True,
            column_config={
                "Item D (Texto Analisado)": st.column_config.TextColumn("Item D (Texto)", width="large"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Início (B)": st.column_config.TextColumn("Início", width="medium"),
                "Fim (C)": st.column_config.TextColumn("Fim", width="medium"),
            },
            height=600
        )