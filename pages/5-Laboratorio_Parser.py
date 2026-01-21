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
# ABA 1: TESTE MANUAL (CÓDIGO ANTERIOR)
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
    st.subheader("🤖 Varredura Automática de Erros")
    st.markdown("Este teste baixa NOTAMs reais e verifica se o parser consegue ler o Item D de todos eles.")

    col_conf1, col_conf2 = st.columns([3, 1])
    
    with col_conf1:
        # Input para ICAO codes (para não baixar o Brasil todo e demorar muito)
        icaos_teste = st.text_input(
            "Filtrar Localidades (Separados por vírgula):", 
            value="SBGR, SBGL, SBSP, SBBR, SBRJ, SBCF, SBSV, SBFZ, SBPA, SBCT, SBEG, SBBE"
        )
    
    with col_conf2:
        st.write("") # Espaço
        st.write("") 
        btn_iniciar = st.button("🚀 Iniciar Varredura", type="primary")

    # Credenciais (Fixas conforme fornecido, ou via secrets em produção)
    API_URL = "https://aisweb.decea.mil.br/api/"
    API_KEY = "1279934730"
    API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"

    if btn_iniciar:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # 1. Monta a URL
        locais = icaos_teste.replace(" ", "")
        url_full = f"{API_URL}?apiKey={API_KEY}&apiPass={API_PASS}&area=notam&icaocode={locais}"
        
        status_text.info("📡 Conectando ao AISWEB...")
        
        try:
            response = requests.get(url_full, timeout=30)
            
            if response.status_code != 200:
                st.error(f"Erro na API: {response.status_code}")
                st.stop()
                
            # 2. Parse do XML retornado pela API
            root = ET.fromstring(response.content)
            items = root.findall("notam")
            total_items = len(items)
            
            if total_items == 0:
                st.warning("Nenhum NOTAM encontrado para esses filtros.")
                st.stop()
                
            status_text.info(f"Analisando {total_items} NOTAMs...")
            
            resultados_lote = []
            
            # 3. Loop de Análise
            for i, item in enumerate(items):
                # Atualiza barra
                progress_bar.progress((i + 1) / total_items)
                
                # Extrai dados básicos
                notam_id = item.find("notam_id").text if item.find("notam_id") is not None else "?"
                loc = item.find("loc").text if item.find("loc") is not None else "?"
                dt_ini_xml = item.find("dt_ini").text # Formato API: pode variar
                dt_fim_xml = item.find("dt_fim").text
                texto_full = item.find("texto").text if item.find("texto") is not None else ""
                
                # --- EXTRAÇÃO DO ITEM D ---
                # A API retorna o texto completo. Precisamos achar o "D)"
                # Regex: Procura "D)" seguido de texto, até encontrar "E)" ou fim da linha/texto
                match_d = re.search(r'(?:^|\s)D\)\s*(.*?)(?=\s*[E-G]\)|\s*$)', texto_full, re.DOTALL)
                
                item_d_extraido = match_d.group(1).strip() if match_d else None
                
                # Lógica de Classificação
                status_analise = "N/A" # Se não tiver Item D
                detalhe_erro = ""
                
                if item_d_extraido:
                    # Tenta rodar o parser
                    # Precisamos converter datas da API (ex: 2025-01-01 10:00) para formato parser (YYMMDDHHMM)
                    # Simplificação: O parser aceita datetime objects ou strings
                    # Vamos tentar passar strings limpas se possível, mas o parser espera YYMMDD...
                    # Para o teste, vamos usar a string bruta da API e ver se o parser converte,
                    # ou converter aqui. A API AISWEB retorna YYYY-MM-DD HH:MM:SS geralmente.
                    
                    try:
                        # Pequeno helper de conversão rápida para o teste
                        def fmt_api_date(d_str):
                            if not d_str: return "2501010000" # Dummy
                            try:
                                dt = datetime.strptime(d_str, "%Y-%m-%d %H:%M:%S")
                                return dt.strftime("%y%m%d%H%M")
                            except: return "2501010000"

                        b_fmt = fmt_api_date(dt_ini_xml)
                        c_fmt = fmt_api_date(dt_fim_xml)
                        
                        # O GRANDE TESTE
                        res_parser = parser_notam.interpretar_periodo_atividade(item_d_extraido, loc, b_fmt, c_fmt)
                        
                        if res_parser:
                            status_analise = "SUCESSO"
                        else:
                            status_analise = "FALHA" # Tem texto D, mas retornou vazio
                            
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
            
            # 4. Exibição dos Resultados
            df_lote = pd.DataFrame(resultados_lote)
            
            # Filtra apenas o que interessa: Onde houve FALHA
            df_falhas = df_lote[df_lote['Status'].isin(["FALHA", "ERRO CÓDIGO"])]
            df_sucesso = df_lote[df_lote['Status'] == "SUCESSO"]
            
            st.divider()
            
            # Métricas
            km1, km2, km3 = st.columns(3)
            km1.metric("Total Analisado", total_items)
            km2.metric("Sucesso (Item D lido)", len(df_sucesso))
            km3.metric("⚠️ Falhas de Parser", len(df_falhas), delta_color="inverse")
            
            if not df_falhas.empty:
                st.error(f"🚨 Encontramos {len(df_falhas)} NOTAMs com Item D que o sistema não entendeu!")
                st.markdown("Envie estes textos para ajuste do código:")
                
                st.dataframe(
                    df_falhas, 
                    use_container_width=True,
                    column_config={
                        "Item D": st.column_config.TextColumn("Texto Item D (Problemático)", width="large"),
                        "Status": st.column_config.TextColumn("Status", width="small"),
                    }
                )
            else:
                st.success("🎉 Incrível! Nenhum erro de interpretação encontrado nos NOTAMs baixados.")
            
            with st.expander("Ver todos os NOTAMs (Incluindo Sucessos)"):
                st.dataframe(df_lote)
                
        except Exception as e:
            st.error(f"Erro fatal na conexão ou processamento: {e}")