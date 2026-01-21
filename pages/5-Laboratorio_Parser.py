import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timedelta
from utils import parser_notam

st.set_page_config(page_title="Lab Parser Item D", layout="wide")
st.title("🛠️ Laboratório de Testes: Parser NOTAM")
st.markdown("""
Ferramenta para validação do algoritmo de interpretação de horários.
""")

tab_manual, tab_lote = st.tabs(["🧪 Teste Manual", "📦 Teste em Lote (API Real)"])

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
        
        st.caption(f"Vigência simulada: {dt_b.strftime('%d/%m/%Y')} a {dt_c.strftime('%d/%m/%Y')}")

    with c2:
        st.subheader("2. Texto (Item D)")
        exemplos = {
            "Padrão Diário": "DLY 0600-1200",
            "Dias da Semana": "MON TIL FRI 1000/1600",
            "Exceção Fim de Semana": "DLY 0800-1700 EXC SAT SUN",
            "Nascer ao Pôr do Sol": "DLY SR-SS",
            "Livre para digitar": ""
        }
        escolha = st.selectbox("Modelos:", list(exemplos.keys()))
        texto_padrao = exemplos[escolha] if escolha != "Livre para digitar" else ""
        item_d_input = st.text_area("Digite o Item D:", value=texto_padrao, height=100)

    if st.button("🔬 Analisar Manualmente", type="primary"):
        if not item_d_input:
            st.warning("Digite algo no Item D.")
            st.stop()
        
        try:
            resultado = parser_notam.interpretar_periodo_atividade(item_d_input, "SBGR", str_b, str_c)
            
            if not resultado:
                st.error("❌ O parser não identificou padrões.")
            else:
                df_res = pd.DataFrame(resultado)
                df_res['Dia'] = df_res['inicio'].dt.strftime('%d/%m/%Y (%a)')
                df_res['Hora'] = df_res['inicio'].dt.strftime('%H:%M') + " - " + df_res['fim'].dt.strftime('%H:%M')
                st.success(f"✅ Identificados {len(df_res)} períodos.")
                st.dataframe(df_res[['Dia', 'Hora']], use_container_width=True, height=300)
        except Exception as e:
            st.error(f"Erro: {e}")

# ==============================================================================
# ABA 2: TESTE EM LOTE (API REAL - CORRIGIDO FIRs)
# ==============================================================================
with tab_lote:
    st.subheader("🤖 Varredura Automática de Erros (Brasil)")
    st.markdown("Baixa NOTAMs reais e verifica se o parser consegue ler o Item D.")

    col_conf1, col_conf2 = st.columns([3, 1])
    
    with col_conf1:
        # Checkbox Brasil Todo
        brasil_todo = st.checkbox("🌍 Analisar BRASIL INTEIRO (Iterar por FIRs)", value=True)
        
        if not brasil_todo:
            icaos_teste = st.text_input(
                "Filtrar Localidades (Separados por vírgula):", 
                value="SBGR, SBGL, SBSP, SBBR, SBRJ, SBCF"
            )
        else:
            # CORRIGIDO AQUI: SBCW em vez de SBWJ
            st.info("Será feita uma varredura nas 5 FIRs do Brasil (SBBS, SBCW, SBRE, SBAZ, SBAO).")
    
    with col_conf2:
        st.write("") 
        st.write("") 
        btn_iniciar = st.button("🚀 Iniciar Varredura", type="primary")

    API_URL = "https://aisweb.decea.mil.br/api/"
    API_KEY = "1279934730"
    API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"

    if btn_iniciar:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # --- ESTRATÉGIA DE BUSCA (FIR vs ICAO) ---
        lista_urls = []
        
        if brasil_todo:
            # CORRIGIDO: SBCW (Curitiba) no lugar de SBWJ
            firs = ['SBBS', 'SBCW', 'SBRE', 'SBAZ', 'SBAO']
            for fir in firs:
                lista_urls.append(f"{API_URL}?apiKey={API_KEY}&apiPass={API_PASS}&area=notam&fir={fir}")
        else:
            locais = icaos_teste.replace(" ", "")
            lista_urls.append(f"{API_URL}?apiKey={API_KEY}&apiPass={API_PASS}&area=notam&icaocode={locais}")
        
        todos_items_xml = []
        
        # --- LOOP DE REQUISIÇÕES ---
        try:
            for idx, url in enumerate(lista_urls):
                msg_status = f"Baixando dados... ({idx+1}/{len(lista_urls)})"
                status_text.info(msg_status)
                
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    try:
                        root = ET.fromstring(response.content)
                        items = root.findall("notam")
                        todos_items_xml.extend(items)
                    except ET.ParseError:
                        st.warning(f"Erro ao ler XML da requisição {idx+1}")
                else:
                    st.error(f"Erro API na requisição {idx+1}: {response.status_code}")

            total_items = len(todos_items_xml)
            
            if total_items == 0:
                st.warning("Nenhum NOTAM encontrado. Verifique se a API está online.")
                st.stop()
                
            status_text.info(f"Analisando {total_items} NOTAMs encontrados...")
            
            resultados_lote = []
            
            # Helper Data
            def fmt_api_date(d_str):
                if not d_str: return "2501010000"
                try:
                    dt = datetime.strptime(d_str, "%Y-%m-%d %H:%M:%S")
                    return dt.strftime("%y%m%d%H%M")
                except: return "2501010000"

            # Helper Extração Segura
            def safe_get_text(xml_item, tag_name):
                found = xml_item.find(tag_name)
                if found is not None and found.text:
                    return found.text
                return ""

            # --- LOOP DE ANÁLISE ---
            for i, item in enumerate(todos_items_xml):
                # Barra de progresso
                if i % (total_items // 20 + 1) == 0:
                    progress_bar.progress((i + 1) / total_items)
                
                notam_id = safe_get_text(item, "notam_id")
                loc = safe_get_text(item, "loc")
                dt_ini_xml = safe_get_text(item, "dt_ini")
                dt_fim_xml = safe_get_text(item, "dt_fim")
                texto_full = safe_get_text(item, "texto")
                
                # Regex Item D
                match_d = re.search(r'(?:^|\s)D\)\s*(.*?)(?=\s*[E-G]\)|\s*$)', texto_full, re.DOTALL)
                item_d_extraido = match_d.group(1).strip() if match_d else None
                
                status_analise = "N/A"
                
                if item_d_extraido:
                    if item_d_extraido.upper() in ["NIL", "NONE", ""]:
                        status_analise = "IGNORADO (NIL)"
                    else:
                        try:
                            b_fmt = fmt_api_date(dt_ini_xml)
                            c_fmt = fmt_api_date(dt_fim_xml)
                            res_parser = parser_notam.interpretar_periodo_atividade(item_d_extraido, loc, b_fmt, c_fmt)
                            
                            if res_parser:
                                status_analise = "SUCESSO"
                            else:
                                status_analise = "FALHA"
                        except Exception as e:
                            status_analise = "ERRO CÓDIGO"

                else:
                    status_analise = "SEM ITEM D"

                resultados_lote.append({
                    "LOC": loc,
                    "NOTAM": notam_id,
                    "Item D": item_d_extraido if item_d_extraido else "-",
                    "Status": status_analise
                })
            
            progress_bar.progress(100)
            status_text.success(f"Análise concluída! Processados {total_items} NOTAMs.")
            
            # --- RESULTADOS ---
            df_lote = pd.DataFrame(resultados_lote)
            df_falhas = df_lote[df_lote['Status'].isin(["FALHA", "ERRO CÓDIGO"])]
            
            # Remove duplicatas
            if not df_falhas.empty:
                df_falhas_unicas = df_falhas.drop_duplicates(subset=['Item D'])
            else:
                df_falhas_unicas = df_falhas

            st.divider()
            
            km1, km2, km3 = st.columns(3)
            km1.metric("Total", total_items)
            km2.metric("Sucesso", len(df_lote) - len(df_falhas))
            km3.metric("⚠️ Falhas Reais", len(df_falhas_unicas), delta_color="inverse")
            
            if not df_falhas_unicas.empty:
                st.error(f"Encontramos {len(df_falhas_unicas)} textos não reconhecidos.")
                st.dataframe(
                    df_falhas_unicas[['LOC', 'NOTAM', 'Item D', 'Status']], 
                    use_container_width=True,
                    column_config={"Item D": st.column_config.TextColumn("Texto D", width="large")}
                )
            else:
                st.success("🎉 Nenhum erro encontrado nos dados baixados!")
            
        except Exception as e:
            st.error(f"Erro fatal durante a execução: {e}")