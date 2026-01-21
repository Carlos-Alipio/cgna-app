import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import parser_notam, db_manager

st.set_page_config(page_title="Lab Parser Item D", layout="wide")
st.title("🛠️ Laboratório de Testes: Parser NOTAM")
st.markdown("Ferramenta para validação do algoritmo usando dados reais do **Banco de Dados (Supabase)**.")

tab_manual, tab_banco = st.tabs(["🧪 Teste Manual", "💾 Auditoria do Banco de Dados"])

# ==============================================================================
# ABA 1: TESTE MANUAL
# ==============================================================================
with tab_manual:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("1. Contexto")
        dt_hoje = datetime.now()
        dt_b = st.date_input("Início (Item B)", value=dt_hoje)
        str_c_manual = st.text_input("Fim (Item C)", value=(dt_hoje + timedelta(days=365)).strftime("%y%m%d")+"2359", help="Digite data YYMMDDHHMM ou 'PERM'")
        str_b = dt_b.strftime("%y%m%d") + "0000"
        
    with c2:
        st.subheader("2. Texto (Item D)")
        exemplos = {
            "Padrão Diário": "DLY 0600-1200",
            "Dias da Semana": "MON TIL FRI 1000/1600",
            "Exceção Fim de Semana": "DLY 0800-1700 EXC SAT SUN",
        }
        escolha = st.selectbox("Modelos:", list(exemplos.keys()))
        texto_padrao = exemplos[escolha]
        item_d_input = st.text_area("Digite o Item D:", value=texto_padrao, height=100)

    if st.button("🔬 Analisar Manualmente", type="primary"):
        try:
            res = parser_notam.interpretar_periodo_atividade(item_d_input, "TESTE", str_b, str_c_manual)
            if not res:
                st.warning("⚠️ Retorno vazio.")
            else:
                df_res = pd.DataFrame(res)
                df_res['Dia'] = df_res['inicio'].dt.strftime('%d/%m/%Y (%a)')
                df_res['Hora'] = df_res['inicio'].dt.strftime('%H:%M') + " - " + df_res['fim'].dt.strftime('%H:%M')
                st.success(f"✅ Identificados {len(df_res)} períodos.")
                dt_final_calc = res[-1]['fim']
                st.info(f"📅 Data Final Calculada: {dt_final_calc.strftime('%d/%m/%Y %H:%M')}")
                st.dataframe(df_res[['Dia', 'Hora']], use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")

# ==============================================================================
# ABA 2: AUDITORIA DO BANCO DE DADOS
# ==============================================================================
with tab_banco:
    st.subheader("🕵️ Auditoria: Supabase")

    # BOTÕES DE AÇÃO
    c_btn1, c_btn2 = st.columns([1, 3])
    
    with c_btn1:
        if st.button("🔄 Carregar/Atualizar Dados", type="primary"):
            st.session_state['force_load'] = True

    with c_btn2:
        if st.button("♻️ Aplicar Regra PERM (365 dias) no Banco Atual"):
            with st.spinner("Reescrevendo banco de dados com a nova regra de 365 dias..."):
                df_atual = db_manager.carregar_notams()
                if not df_atual.empty:
                    # Ao salvar, a função corrigida do db_manager aplica a regra PERM
                    sucesso = db_manager.salvar_notams(df_atual)
                    if sucesso:
                        st.success("✅ Banco atualizado! Registros PERM corrigidos.")
                        st.session_state['force_load'] = True
                        st.rerun()
                    else:
                        st.error("Erro ao salvar o banco.")

    # LÓGICA DE CARREGAMENTO E EXIBIÇÃO
    if st.session_state.get('force_load', False):
        with st.spinner("Carregando e processando datas..."):
            df_full = db_manager.carregar_notams()
            
            if df_full.empty:
                st.warning("Banco vazio.")
            else:
                col_d = 'd'
                # Filtra apenas o necessário
                df_analise = df_full[~df_full[col_d].astype(str).str.upper().isin(["NIL", "NONE"])].copy()
                
                total = len(df_analise)
                progress_bar = st.progress(0)
                resultados = []

                def basic_parse(val):
                    s = str(val).strip().upper()
                    clean = s.replace("-", "").replace(":", "").replace(" ", "")
                    if len(clean) == 10 and clean.isdigit(): return datetime.strptime(clean, "%y%m%d%H%M")
                    if isinstance(val, (datetime, pd.Timestamp)): return val
                    return None

                for idx, row in enumerate(df_analise.iterrows()):
                    r = row[1]
                    if idx % 50 == 0: progress_bar.progress(min((idx + 1) / total, 1.0))
                    
                    item_d = str(r[col_d]).strip()
                    if item_d.lower() == 'nan': item_d = ""
                    loc = r.get('loc', 'SB??')
                    n_notam = r.get('n', '?')
                    
                    raw_b = r.get('b', '')
                    raw_c = r.get('c', '')

                    # Parse básico para visualização
                    dt_b_obj = basic_parse(raw_b)
                    if not dt_b_obj: dt_b_obj = datetime.now()
                    
                    # Se tiver PERM aqui, é porque o banco já foi corrigido ou ainda não
                    # Para visualização, tentamos parsear. 
                    # Se o botão de "Aplicar Regra" foi usado, raw_c já será uma data futura.
                    dt_c_obj = basic_parse(raw_c)

                    str_b_parser = dt_b_obj.strftime("%y%m%d%H%M")
                    str_c_parser = dt_c_obj.strftime("%y%m%d%H%M") if dt_c_obj else None
                    
                    status = "N/A"
                    detalhe = "-"
                    
                    try:
                        res = parser_notam.interpretar_periodo_atividade(item_d, loc, str_b_parser, str_c_parser)
                        if res:
                            status = "SUCESSO"
                            dias_str = ", ".join([d['inicio'].strftime('%d/%m') for d in res[:3]])
                            if len(res) > 3: dias_str += "..."
                            detalhe = f"{len(res)} dias ({dias_str})"
                        else:
                            status = "FALHA"
                            detalhe = "Retorno Vazio []"
                    except Exception as e:
                        status = "ERRO CÓDIGO"
                        detalhe = str(e)

                    resultados.append({
                        "LOC": loc,
                        "NOTAM": n_notam,
                        "Item D": item_d,
                        "Início (B)": dt_b_obj,
                        "Fim (C)": dt_c_obj,
                        "Status": status,
                        "Detalhe": detalhe
                    })
                
                progress_bar.progress(100)
                st.session_state['auditoria_resultados'] = pd.DataFrame(resultados)
                st.session_state['force_load'] = False # Reseta trigger
                st.rerun()

    # RENDERIZA A TABELA SE JÁ ESTIVER CARREGADA
    if 'auditoria_resultados' in st.session_state:
        df_res = st.session_state['auditoria_resultados']
        
        st.divider()
        k1, k2, k3 = st.columns(3)
        k1.metric("Total", len(df_res))
        k2.metric("Sucessos", len(df_res[df_res['Status'] == 'SUCESSO']))
        k3.metric("Falhas", len(df_res[df_res['Status'] != 'SUCESSO']), delta_color="inverse")
        
        st.dataframe(
            df_res,
            use_container_width=True,
            column_config={
                "Item D": st.column_config.TextColumn("Texto (Item D)", width="large"),
                "Detalhe": st.column_config.TextColumn("Resultado", width="medium"),
                "Início (B)": st.column_config.DatetimeColumn("Vigência Ini", format="DD/MM/YYYY HH:mm"),
                "Fim (C)": st.column_config.DatetimeColumn("Vigência Fim", format="DD/MM/YYYY HH:mm"),
            },
            height=600
        )