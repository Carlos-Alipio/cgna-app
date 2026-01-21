import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timedelta
from utils import parser_notam

st.set_page_config(page_title="Lab Parser Item D", layout="wide")
st.title("🛠️ Laboratório: Diagnóstico de Dados")
st.markdown("Use esta tela para descobrir por que o Item D não está sendo encontrado.")

tab_manual, tab_lote = st.tabs(["🧪 Teste Manual", "📦 Auditoria em Lote (Debug)"])

# ==============================================================================
# ABA 1: TESTE MANUAL (MANTIDA IGUAL)
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
# ABA 2: DIAGNÓSTICO EM LOTE
# ==============================================================================
with tab_lote:
    st.subheader("🕵️ Espião de XML (Debug)")
    st.info("Esta ferramenta vai mostrar o texto cru que vem da API para entendermos o erro.")

    col_conf1, col_conf2 = st.columns([3, 1])
    with col_conf1:
        # Padrão: Buscar Brasil Todo para pegar massa de dados
        brasil_todo = st.checkbox("Analisa Brasil Todo (5 FIRs)", value=True)
        if not brasil_todo:
            icaos_teste = st.text_input("Filtrar Localidades:", value="SBGR, SBGL, SBSP")
    with col_conf2:
        st.write("")
        btn_iniciar = st.button("🚀 Iniciar Diagnóstico", type="primary")

    API_URL = "http://aisweb.decea.mil.br/api/"
    API_KEY = "1279934730"
    API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"

    if btn_iniciar:
        status_text = st.empty()
        
        # --- 1. BUSCA ---
        if brasil_todo:
            icaos_consulta = "SBAZ,SBBS,SBCW,SBRE,SBAO"
        else:
            icaos_consulta = icaos_teste.replace(" ", "")

        status_text.info(f"📡 Baixando dados...")
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
        st.write(f"**Total de NOTAMs baixados:** {total_items}")

        # --- 2. ESPIONAGEM (MOSTRAR OS PRIMEIROS 5 NOTAMS COMPLETOS) ---
        st.divider()
        st.markdown("### 🔍 Raio-X dos 5 primeiros registros")
        st.markdown("Veja abaixo como o texto está chegando e se a tag `<texto>` existe.")

        for i in range(min(5, total_items)):
            item = todos_items_xml[i]
            
            # Tenta pegar tags comuns
            raw_text = item.find("texto").text if item.find("texto") is not None else "TAG <texto> NÃO ENCONTRADA"
            raw_id = item.find("notam_id").text if item.find("notam_id") is not None else "?"
            
            with st.expander(f"NOTAM #{i+1}: {raw_id}", expanded=True):
                st.code(raw_text, language="text")
                
                # Teste da Regex ao vivo
                match_d = re.search(r'(?:^|\s|\n)D\)\s*(.+?)(?=\s*[E-G]\)|\s*$)', raw_text, re.DOTALL | re.IGNORECASE)
                if match_d:
                    st.success(f"✅ Regex encontrou: '{match_d.group(1).strip()}'")
                else:
                    st.error("❌ Regex NÃO encontrou o padrão 'D)' neste texto.")

        # --- 3. PROCESSAMENTO GERAL ---
        st.divider()
        st.markdown("### 📊 Tentativa de Processamento em Massa")
        
        resultados_lote = []
        
        def fmt_api_date(d_str):
            if not d_str: return "2501010000"
            try: return datetime.strptime(d_str, "%Y-%m-%d %H:%M:%S").strftime("%y%m%d%H%M")
            except: return "2501010000"

        for item in todos_items_xml:
            # Extração Segura
            texto = item.find("texto").text if item.find("texto") is not None else ""
            notam_id = item.find("notam_id").text if item.find("notam_id") is not None else "?"
            loc = item.find("loc").text if item.find("loc") is not None else "?"
            
            # --- REGEX MELHORADA ---
            # Procura D) no inicio da linha, ou após espaço, ou após newline
            # Captura tudo até achar E), F), G) ou fim da string
            match_d = re.search(r'(?:^|\s|\n)D\)\s*(.+?)(?=\s*[E-G]\)|\s*$)', texto, re.DOTALL | re.IGNORECASE)
            item_d = match_d.group(1).strip() if match_d else None
            
            status = "SEM ITEM D"
            
            if item_d:
                if item_d.upper() in ["NIL", "NONE", ""]:
                    status = "IGNORADO (NIL)"
                else:
                    # Tenta rodar o parser
                    try:
                        dt_ini = item.find("dt_ini").text
                        dt_fim = item.find("dt_fim").text
                        res = parser_notam.interpretar_periodo_atividade(
                            item_d, loc, fmt_api_date(dt_ini), fmt_api_date(dt_fim)
                        )
                        status = "SUCESSO" if res else "FALHA PARSER"
                    except:
                        status = "ERRO CODIGO"

            resultados_lote.append({
                "NOTAM": notam_id,
                "Texto Bruto (Início)": texto[:50] + "...",
                "Item D Extraído": item_d if item_d else "-",
                "Status": status
            })

        df = pd.DataFrame(resultados_lote)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", len(df))
        c2.metric("Com Item D (Regex pegou)", len(df[df['Item D Extraído'] != '-']))
        c3.metric("Sucesso Parser", len(df[df['Status'] == 'SUCESSO']))

        st.dataframe(df, use_container_width=True)