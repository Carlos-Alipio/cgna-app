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

    API_URL = "http://aisweb.decea.mil.br/api/"
    API_KEY = "1279934730"
    API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"

    if btn_iniciar:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # --- BUSCA ---
        if brasil_todo:
            icaos_consulta = "SBAZ,SBBS,SBCW,SBRE,SBAO"
            msg_busca = "Baixando dados completos das 5 FIRs..."
        else:
            icaos_consulta = icaos_teste.replace(" ", "")
            msg_busca = f"Baixando dados de: {icaos_consulta}..."

        status_text.info(f"📡 {msg_busca}")
        todos_items_xml = []
        
        try:
            params = {
                'apiKey': API_KEY, 'apiPass': API_PASS, 'area': 'notam', 'icaocode': icaos_consulta
            }
            response = requests.get(API_URL, params=params, timeout=60)
            if response.status_code == 200:
                try:
                    root = ET.fromstring(response.content)
                    todos_items_xml = root.findall("notam")
                except:
                    st.error("XML inválido.")
                    st.stop()
            else:
                st.error(f"Erro API: {response.status_code}")
                st.stop()
        except Exception as e:
            st.error(f"Erro conexão: {e}")
            st.stop()

        total_items = len(todos_items_xml)
        if total_items == 0:
            st.warning("Nenhum dado.")
            st.stop()

        status_text.info(f"Processando {total_items} NOTAMs...")
        resultados_lote = []

        def fmt_api_date(d_str):
            if not d_str: return "2501010000"
            try: return datetime.strptime(d_str, "%Y-%m-%d %H:%M:%S").strftime("%y%m%d%H%M")
            except: return "2501010000"

        def safe_get(item, tag):
            f = item.find(tag)
            return f.text if f is not None and f.text else ""

        # --- LOOP ANÁLISE ---
        count_com_item_d = 0
        
        for i, item in enumerate(todos_items_xml):
            if i % (total_items // 20 + 1) == 0: progress_bar.progress((i + 1) / total_items)
            
            notam_id = safe_get(item, "notam_id")
            loc = safe_get(item, "loc")
            dt_ini = safe_get(item, "dt_ini")
            dt_fim = safe_get(item, "dt_fim")
            texto = safe_get(item, "texto")
            
            match_d = re.search(r'(?:^|\s)D\)\s*(.*?)(?=\s*[E-G]\)|\s*$)', texto, re.DOTALL)
            item_d = match_d.group(1).strip() if match_d else None
            
            # SÓ ADICIONA NA LISTA SE TIVER ITEM D VÁLIDO (IGNORA NIL/NONE)
            if item_d and item_d.upper() not in ["NIL", "NONE", ""]:
                count_com_item_d += 1
                status = "N/A"
                res_visual = "-"
                
                try:
                    res = parser_notam.interpretar_periodo_atividade(
                        item_d, loc, fmt_api_date(dt_ini), fmt_api_date(dt_fim)
                    )
                    if res:
                        status = "SUCESSO"
                        # Cria um resumo visual: "5 dias (20/01, 21/01...)"
                        dias_str = ", ".join([d['inicio'].strftime('%d/%m') for d in res[:3]])
                        if len(res) > 3: dias_str += "..."
                        res_visual = f"{len(res)} dias ({dias_str})"
                    else:
                        status = "FALHA"
                        res_visual = "Retornou Vazio"
                except:
                    status = "ERRO CÓDIGO"
                    res_visual = "Crash"

                resultados_lote.append({
                    "LOC": loc,
                    "NOTAM": notam_id,
                    "Início (B)": dt_ini,
                    "Fim (C)": dt_fim,
                    "Item D (Texto)": item_d,
                    "Status": status,
                    "Resultado Parser": res_visual
                })

        progress_bar.progress(100)
        status_text.success("Concluído!")
        
        # --- EXIBIÇÃO ---
        df = pd.DataFrame(resultados_lote)
        
        st.divider()
        st.markdown(f"### 🕵️ Análise: {len(df)} NOTAMs com Campo 'D' encontrados")
        
        # Filtros
        filtro = st.radio(
            "Filtrar Lista:", 
            ["📜 Todos com Item D", "✅ Apenas Sucessos", "🚨 Apenas Falhas"],
            horizontal=True
        )
        
        if filtro == "🚨 Apenas Falhas":
            df_show = df[df['Status'].isin(["FALHA", "ERRO CÓDIGO"])]
            st.error(f"{len(df_show)} casos onde o robô não entendeu o texto.")
        elif filtro == "✅ Apenas Sucessos":
            df_show = df[df['Status'] == "SUCESSO"]
            st.success(f"{len(df_show)} casos interpretados com sucesso.")
        else:
            df_show = df
            st.info(f"Listando todos os {len(df_show)} NOTAMs que possuem restrição de horário.")

        # Tabela Rica
        st.dataframe(
            df_show,
            use_container_width=True,
            column_config={
                "Item D (Texto)": st.column_config.TextColumn("Texto Original (D)", width="large"),
                "Resultado Parser": st.column_config.TextColumn("O que o Robô Entendeu", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Início (B)": st.column_config.TextColumn("Vigência Ini", width="small"),
                "Fim (C)": st.column_config.TextColumn("Vigência Fim", width="small"),
            },
            height=600
        )
        
        # Botão Download
        csv = df_show.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Baixar Lista para Excel (CSV)",
            data=csv,
            file_name="analise_item_d.csv",
            mime="text/csv"
        )