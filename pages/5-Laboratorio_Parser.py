import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timedelta
from utils import parser_notam

st.set_page_config(page_title="Lab Parser & Debug", layout="wide")
st.title("🛠️ Laboratório: Diagnóstico de Estrutura XML")
st.markdown("Use esta tela para **descobrir os nomes corretos** das tags da API.")

tab_manual, tab_debug = st.tabs(["🧪 Teste Manual", "🕵️ Espião de XML (Debug)"])

# ==============================================================================
# ABA 1: TESTE MANUAL (MANTIDA)
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
# ABA 2: ESPIÃO DE XML (PARA DESCOBRIR AS TAGS)
# ==============================================================================
with tab_debug:
    st.subheader("🕵️ Raio-X da API")
    st.info("Vamos listar TODAS as tags que a API devolve para descobrir onde está o texto.")

    col_conf1, col_conf2 = st.columns([3, 1])
    with col_conf1:
        # Checkbox para usar as 5 FIRs ou filtro manual
        usar_firs = st.checkbox("Consultar Brasil Todo (5 FIRs)", value=True)
        if not usar_firs:
            icaos_teste = st.text_input("Filtrar ICAO:", value="SBGR")
    with col_conf2:
        st.write("")
        btn_debug = st.button("🚀 Rodar Diagnóstico", type="primary")

    # URL fornecida por você
    API_URL = "http://aisweb.decea.mil.br/api/"
    API_KEY = "1279934730"
    API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"

    if btn_debug:
        status_text = st.empty()
        
        # Define icaocode
        if usar_firs:
            icaocode_param = "SBAZ,SBBS,SBCW,SBRE,SBAO"
        else:
            icaocode_param = icaos_teste.replace(" ", "")

        status_text.info("📡 Conectando à API...")
        
        try:
            params = {
                'apiKey': API_KEY, 
                'apiPass': API_PASS, 
                'area': 'notam', 
                'icaocode': icaocode_param
            }
            
            # Timeout alto para garantir download
            response = requests.get(API_URL, params=params, timeout=60)
            
            if response.status_code != 200:
                st.error(f"Erro HTTP {response.status_code}")
                st.stop()

            # Parse do XML
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError:
                st.error("O conteúdo retornado não é um XML válido.")
                st.text(response.text[:500]) # Mostra o início para ver se é HTML de erro
                st.stop()
                
            # Busca itens <notam>
            items = root.findall("notam")
            total_items = len(items)
            
            st.markdown(f"**Status:** Encontrados `{total_items}` registros dentro da tag `<notam>`.")

            if total_items == 0:
                st.warning("Nenhuma tag <notam> encontrada. Mostrando tags da raiz:")
                # Mostra o que tem na raiz para entender o erro
                root_tags = {child.tag: child.text for child in root}
                st.json(root_tags)
                st.stop()

            # --- O PULO DO GATO: MOSTRAR AS TAGS REAIS ---
            st.divider()
            st.subheader("🔍 Estrutura do 1º NOTAM encontrado")
            st.markdown("Verifique abaixo qual é o nome do campo que contém o texto (ex: `txt`, `conteudo`, `body`).")
            
            primeiro_item = items[0]
            
            # Cria um dicionário com TODAS as tags deste item
            tags_reais = {}
            for child in primeiro_item:
                # Salva nome da tag e os primeiros 100 caracteres do conteúdo
                conteudo = str(child.text).strip() if child.text else ""
                tags_reais[child.tag] = conteudo[:200] + ("..." if len(conteudo) > 200 else "")
            
            # Exibe o JSON colorido para fácil leitura
            st.json(tags_reais)
            
            st.info("👆 **Olhe acima:** Qual tag contém a descrição do NOTAM? Use esse nome para corrigir o parser.")

            # --- LISTAGEM TABULAR SIMPLES (PREVIEW) ---
            st.divider()
            st.subheader("📋 Preview dos 10 primeiros (Baseado na descoberta)")
            
            lista_preview = []
            for item in items[:10]:
                # Tenta pegar tags comuns na "força bruta" para preencher a tabela
                dados = {}
                for child in item:
                    dados[child.tag] = child.text
                lista_preview.append(dados)
            
            st.dataframe(pd.DataFrame(lista_preview))

        except Exception as e:
            st.error(f"Erro fatal: {e}")