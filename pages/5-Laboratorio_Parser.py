import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import parser_notam, db_manager

st.set_page_config(page_title="Lab Parser Item D", layout="wide")
st.title("🛠️ Laboratório de Testes: Parser NOTAM")
st.markdown("Ferramenta de **auditoria visual** para validar a interpretação dos NOTAMs.")

tab_manual, tab_banco = st.tabs(["🧪 Teste Manual", "💾 Auditoria do Banco de Dados"])

# ==============================================================================
# ABA 1: TESTE MANUAL (Para simular cenários específicos)
# ==============================================================================
with tab_manual:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("1. Parâmetros")
        dt_hoje = datetime.now()
        dt_b = st.date_input("Início (Item B)", value=dt_hoje)
        # Permite testar a lógica do PERM manualmente
        str_c_manual = st.text_input("Fim (Item C)", value="PERM", help="Digite uma data (YYMMDDHHMM) ou 'PERM'")
        
        # Formata para o padrão do parser (YYMMDDHHMM)
        str_b = dt_b.strftime("%y%m%d") + "0000"
        
    with c2:
        st.subheader("2. Texto (Item D)")
        exemplos = {
            "Sem Texto (H24)": "",
            "Padrão Diário": "DLY 0600-1200",
            "Dias da Semana": "MON TIL FRI 1000/1600",
        }
        escolha = st.selectbox("Carregar Exemplo:", list(exemplos.keys()))
        texto_padrao = exemplos[escolha]
        item_d_input = st.text_area("Conteúdo do Item D:", value=texto_padrao, height=100)

    if st.button("🔬 Analisar Cenário", type="primary"):
        try:
            # Chama o parser exatamente como o sistema chamaria
            res = parser_notam.interpretar_periodo_atividade(item_d_input, "TESTE", str_b, str_c_manual)
            
            if not res:
                st.warning("⚠️ Retorno vazio (Nenhuma atividade detectada ou erro de parse).")
            else:
                df_res = pd.DataFrame(res)
                # Formatação para leitura humana
                df_res['Dia'] = df_res['inicio'].dt.strftime('%d/%m/%Y (%a)')
                df_res['Hora'] = df_res['inicio'].dt.strftime('%H:%M') + " - " + df_res['fim'].dt.strftime('%H:%M')
                
                c_res1, c_res2 = st.columns(2)
                c_res1.success(f"✅ Identificados {len(df_res)} slots de atividade.")
                
                # Mostra a data final que o parser calculou (importante para validar o PERM)
                dt_final_calc = res[-1]['fim']
                c_res2.info(f"📅 Data Final Calculada: {dt_final_calc.strftime('%d/%m/%Y %H:%M')}")
                
                st.dataframe(df_res[['Dia', 'Hora']], use_container_width=True, height=300)
        except Exception as e:
            st.error(f"Erro na execução: {e}")

# ==============================================================================
# ABA 2: AUDITORIA (Visualização do Banco Real)
# ==============================================================================
with tab_banco:
    st.subheader("🕵️ Auditoria: Supabase")
    
    # Botão único e simples para recarregar a visualização
    if st.button("🔄 Atualizar Tabela", type="primary"):
        st.session_state['force_load'] = True

    if st.session_state.get('force_load', False):
        with st.spinner("Lendo dados do banco..."):
            df_full = db_manager.carregar_notams()
            
            if df_full.empty:
                st.warning("O Banco de Dados está vazio.")
            else:
                col_d = 'd'
                # Filtra removendo NIL/NONE para focar no que importa
                df_analise = df_full[~df_full[col_d].astype(str).str.upper().isin(["NIL", "NONE"])].copy()
                
                resultados = []

                # Função auxiliar simples para datas
                def parse_visual(val):
                    s = str(val).strip().upper()
                    clean = s.replace("-", "").replace(":", "").replace(" ", "")
                    # Se for data padrão YYMMDDHHMM
                    if len(clean) == 10 and clean.isdigit(): 
                        return datetime.strptime(clean, "%y%m%d%H%M")
                    # Se já vier como objeto datetime do pandas
                    if isinstance(val, (datetime, pd.Timestamp)): 
                        return val
                    return None

                for idx, row in enumerate(df_analise.iterrows()):
                    r = row[1]
                    
                    item_d = str(r[col_d]).strip()
                    if item_d.lower() == 'nan': item_d = ""
                    
                    loc = r.get('loc', 'SB??')
                    n_notam = r.get('n', '?')
                    
                    # Dados Crus do Banco
                    raw_b = r.get('b', '')
                    raw_c = r.get('c', '') 

                    dt_b_obj = parse_visual(raw_b)
                    if not dt_b_obj: dt_b_obj = datetime.now()
                    
                    # SIMULAÇÃO DA REGRA ESTRITA DO CRONOGRAMA PARA VISUALIZAÇÃO
                    # Aqui mostramos o que o gráfico vai "enxergar"
                    data_final_exibicao = "Erro"
                    
                    # 1. Se tem PERM escrito no banco -> +365 dias
                    if "PERM" in str(raw_c).upper():
                        dt_final = dt_b_obj + timedelta(days=365)
                        data_final_exibicao = f"{dt_final.strftime('%d/%m/%Y')} (PERM Calculado)"
                        str_c_parser = "PERM" # Manda PERM pro parser saber
                    else:
                        # 2. Se tem data, usa a data
                        dt_c_obj = parse_visual(raw_c)
                        if dt_c_obj:
                            data_final_exibicao = dt_c_obj.strftime('%d/%m/%Y %H:%M')
                            str_c_parser = dt_c_obj.strftime("%y%m%d%H%M")
                        else:
                            data_final_exibicao = "Sem Data"
                            str_c_parser = None

                    # Executa o Parser para ver se gera slots
                    str_b_parser = dt_b_obj.strftime("%y%m%d%H%M")
                    
                    status = "N/A"
                    try:
                        res = parser_notam.interpretar_periodo_atividade(item_d, loc, str_b_parser, str_c_parser)
                        if res:
                            status = "✅ OK"
                            detalhe = f"{len(res)} slots gerados"
                        else:
                            status = "⚠️ Vazio"
                            detalhe = "Parser não gerou horários"
                    except Exception as e:
                        status = "❌ Erro"
                        detalhe = str(e)

                    resultados.append({
                        "LOC": loc,
                        "NOTAM": n_notam,
                        "Item D": item_d,
                        "Início": dt_b_obj,
                        "Fim (Banco/Regra)": data_final_exibicao,
                        "Status Parser": status,
                        "Detalhe": detalhe
                    })
                
                df_audit = pd.DataFrame(resultados)
                
                st.divider()
                st.metric("Total de NOTAMs Analisados", len(df_audit))
                
                st.dataframe(
                    df_audit,
                    use_container_width=True,
                    column_config={
                        "Item D": st.column_config.TextColumn("Texto (Item D)", width="large"),
                        "Início": st.column_config.DatetimeColumn("Início", format="DD/MM/YYYY HH:mm"),
                        "Status Parser": st.column_config.TextColumn("Status", width="small"),
                    },
                    height=600
                )