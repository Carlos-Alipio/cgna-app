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
Use o **Teste Manual** para criar cenários ou o **Teste em Lote** para varrer a API em busca de erros reais.
""")

# Abas para separar as funcionalidades
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
            "Datas Específicas": "SEP 05 08 12 20 2200-0200",
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
                with st.expander("JSON Bruto"):
                    st.write(resultado)
        except Exception as e:
            st.error(f"Erro: {e}")

# ==============================================================================
# ABA 2: TESTE EM LOTE (API REAL)
# ==============================================================================
with tab_lote:
    st.subheader("🤖 Varredura Automática de Erros (Brasil)")
    st.markdown("Este teste baixa NOTAMs reais e verifica se o parser consegue ler o Item D.")

    col_conf1, col_conf2 = st.columns([3, 1])
    
    with col_conf1:
        # Opção para Brasil todo
        brasil_todo = st.checkbox("🌍 Analisar BRASIL INTEIRO (Pode demorar uns segundos)", value=True)
        
        if not brasil_todo:
            icaos_teste = st.text_input(
                "Filtrar Localidades (Separados por vírgula):", 
                value="SBGR, SBGL, SBSP, SBBR, SBRJ, SBCF"
            )
        else:
            st.info("O filtro de localidades será ignorado. Buscando todos os NOTAMs ativos no Brasil.")
            icaos_teste = ""
    
    with col_conf2:
        st.write("") 
        st.write("") 
        btn_iniciar = st.button("🚀 Iniciar Varredura", type="primary")

    # Credenciais
    API_URL = "https://aisweb.decea.mil.br/api/"
    API_KEY = "1279934730"
    API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"

    if btn_iniciar:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # 1. Monta a URL
        if brasil_todo:
            # Sem filtro de icaocode = Brasil todo
            url_full = f"{API_URL}?apiKey={API_KEY}&apiPass={API_PASS}&area=notam"
        else:
            locais = icaos_teste.replace(" ", "")
            url_full = f"{API_URL}?apiKey={API_KEY}&apiPass={API_PASS}&area=notam&icaocode={locais}"
        
        status_text.info("📡 Conectando ao AISWEB (Aguarde, baixando XML grande)...")
        
        try:
            # Aumentei o timeout para 60s pois o XML do Brasil todo é pesado
            response = requests.get(url_full, timeout=60)
            
            if response.status_code != 200:
                st.error(f"Erro na API: {response.status_code}")
                st.stop()
                
            # 2. Parse do XML
            status_text.info("Processando XML...")
            root = ET.fromstring(response.content)
            items = root.findall("notam")
            total_items = len(items)
            
            if total_items == 0:
                st.warning("Nenhum NOTAM encontrado.")
                st.stop()
                
            status_text.info(f"Analisando {total_items} NOTAMs encontrados...")
            
            resultados_lote = []
            
            # Helper de data
            def fmt_api_date(d_str):
                if not d_str: return "2501010000"
                try:
                    dt = datetime.strptime(d_str, "%Y-%m-%d %H:%M:%S")
                    return dt.strftime("%y%m%d%H%M")
                except: return "2501010000"
            
            # 3. Loop de Análise
            for i, item in enumerate(items):
                # Atualiza barra a cada 5% para não travar a UI
                if i % (total_items // 20 + 1) == 0:
                    progress_bar.progress((i + 1) / total_items)
                
                notam_id = item.find("notam_id").text if item.find("notam_id") is not None else "?"
                loc = item.find("loc").text if item.find("loc") is not None else "?"
                dt_ini_xml = item.find("dt_ini").text 
                dt_fim_xml = item.find("dt_fim").text
                texto_full = item.find("texto").text if item.find("texto") is not None else ""
                
                # Regex para achar Item D
                match_d = re.search(r'(?:^|\s)D\)\s*(.*?)(?=\s*[E-G]\)|\s*$)', texto_full, re.DOTALL)
                item_d_extraido = match_d.group(1).strip() if match_d else None
                
                status_analise = "N/A" 
                detalhe_erro = ""
                
                if item_d_extraido:
                    # Filtra falsos positivos comuns (ex: "NIL")
                    if item_d_extraido.upper() in ["NIL", "NONE"]:
                        status_analise = "IGNORADO (NIL)"
                    else:
                        try:
                            b_fmt = fmt_api_date(dt_ini_xml)
                            c_fmt = fmt_api_date(dt_fim_xml)
                            
                            res_parser = parser_notam.interpretar_periodo_atividade(item_d_extraido, loc, b_fmt, c_fmt)
                            
                            if res_parser:
                                status_analise = "SUCESSO"
                            else:
                                status_analise = "FALHA" # Tem texto D, mas parser não leu
                                
                        except Exception as e:
                            status_analise = "ERRO CÓDIGO"
                            detalhe_erro = str(e)
                else:
                    status_analise = "SEM ITEM D"

                resultados_lote.append({
                    "LOC": loc,
                    "NOTAM": notam_id,
                    "Item D": item_d_extraido if item_d_extraido else "-",
                    "Status": status_analise,
                    "Erro": detalhe_erro
                })
            
            progress_bar.progress(100)
            status_text.success(f"Análise concluída em {total_items} registros!")
            
            # 4. Exibição
            df_lote = pd.DataFrame(resultados_lote)
            
            # Filtra Falhas Reais
            df_falhas = df_lote[df_lote['Status'].isin(["FALHA", "ERRO CÓDIGO"])]
            
            # Remove duplicatas de texto para facilitar a análise
            # (Muitos NOTAMs repetem o mesmo texto em aeroportos diferentes)
            if not df_falhas.empty:
                df_falhas_unicas = df_falhas.drop_duplicates(subset=['Item D'])
            else:
                df_falhas_unicas = df_falhas

            st.divider()
            
            # Métricas
            km1, km2, km3 = st.columns(3)
            km1.metric("Total Analisado", total_items)
            km2.metric("Sucesso / Sem D", len(df_lote) - len(df_falhas))
            km3.metric("⚠️ Falhas Únicas", len(df_falhas_unicas), delta_color="inverse")
            
            if not df_falhas_unicas.empty:
                st.error(f"🚨 Encontramos {len(df_falhas_unicas)} padrões de texto que o sistema não entendeu!")
                st.markdown("Copie estes textos para ajustar o `parser_notam.py`:")
                
                st.dataframe(
                    df_falhas_unicas[['LOC', 'NOTAM', 'Item D', 'Status']], 
                    use_container_width=True,
                    column_config={
                        "Item D": st.column_config.TextColumn("Texto Item D (Problemático)", width="large"),
                    }
                )
            else:
                st.success("🎉 Incrível! Nenhum erro encontrado em todo o Brasil.")
            
        except Exception as e:
            st.error(f"Erro fatal: {e}")