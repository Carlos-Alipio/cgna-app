import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import parser_notam, db_manager

st.set_page_config(page_title="Lab Parser Item D", layout="wide")
st.title("🛠️ Laboratório de Testes: Parser NOTAM")

tab_manual, tab_banco = st.tabs(["🧪 Teste Manual", "💾 Auditoria do Banco de Dados"])

# ... (Mantenha o conteúdo da aba 'tab_manual' igual ao anterior) ...
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
            "PERM (REF AIP)": "RWY 18/36 CLSD REF: AIP AD 2.12",
            "Padrão Diário": "DLY 0600-1200",
        }
        escolha = st.selectbox("Modelos:", list(exemplos.keys()))
        texto_padrao = exemplos[escolha]
        item_d_input = st.text_area("Digite o Item D:", value=texto_padrao, height=100)

    if st.button("🔬 Analisar Manualmente", type="primary"):
        try:
            res = parser_notam.interpretar_periodo_atividade(item_d_input, "TESTE", str_b, str_c_manual)
            if not res: st.warning("⚠️ Retorno vazio.")
            else:
                df_res = pd.DataFrame(res)
                df_res['Dia'] = df_res['inicio'].dt.strftime('%d/%m/%Y (%a)')
                df_res['Hora'] = df_res['inicio'].dt.strftime('%H:%M') + " - " + df_res['fim'].dt.strftime('%H:%M')
                st.success(f"✅ Identificados {len(df_res)} períodos.")
                dt_final_calc = res[-1]['fim']
                st.info(f"📅 Data Final Calculada: {dt_final_calc.strftime('%d/%m/%Y %H:%M')}")
                st.dataframe(df_res[['Dia', 'Hora']], use_container_width=True)
        except Exception as e: st.error(f"Erro: {e}")

# ==============================================================================
# ABA 2: AUDITORIA E LIMPEZA
# ==============================================================================
with tab_banco:
    st.subheader("🕵️ Auditoria: Supabase")

    # BOTÕES DE AÇÃO
    c_btn1, c_btn2, c_btn3 = st.columns([1, 1.5, 1])
    
    with c_btn1:
        if st.button("🔄 Carregar/Atualizar Visualização", type="primary"):
            st.session_state['force_load'] = True

    # Botão para corrigir usando os dados que já estão lá (sem apagar)
    with c_btn2:
        if st.button("♻️ Re-processar Banco Atual (Regra 365 dias)"):
            with st.spinner("Corrigindo registros existentes..."):
                df_atual = db_manager.carregar_notams()
                if not df_atual.empty:
                    # Ao salvar, o db_manager aplica a correção automaticamente
                    db_manager.salvar_notams(df_atual)
                    st.success("✅ Banco re-processado com sucesso!")
                    st.session_state['force_load'] = True
                    st.rerun()

    # Botão para ZERAR TUDO (Útil antes de rodar seu script de integração)
    with c_btn3:
        if st.button("🗑️ Zerar Banco de Dados", type="secondary"):
            if db_manager.limpar_tabela_notams():
                st.warning("⚠️ Banco de dados foi limpo! Execute seu script de integração para popular novamente.")
                # Limpa cache visual
                if 'auditoria_resultados' in st.session_state:
                    del st.session_state['auditoria_resultados']
                st.rerun()

    # LÓGICA DE CARREGAMENTO (Igual à anterior)
    if st.session_state.get('force_load', False):
        with st.spinner("Carregando..."):
            df_full = db_manager.carregar_notams()
            if df_full.empty:
                st.warning("O Banco de Dados está vazio.")
                # Limpa tabela se estiver vazia
                if 'auditoria_resultados' in st.session_state:
                     del st.session_state['auditoria_resultados']
            else:
                # ... (Mesma lógica de exibição anterior) ...
                col_d = 'd'
                df_analise = df_full[~df_full[col_d].astype(str).str.upper().isin(["NIL", "NONE"])].copy()
                resultados = []
                
                # Barra de progresso simplificada para não travar
                total = len(df_analise)
                
                def basic_parse(val):
                    s = str(val).strip().upper()
                    clean = s.replace("-", "").replace(":", "").replace(" ", "")
                    if len(clean) == 10 and clean.isdigit(): return datetime.strptime(clean, "%y%m%d%H%M")
                    if isinstance(val, (datetime, pd.Timestamp)): return val
                    return None

                for idx, row in enumerate(df_analise.iterrows()):
                    r = row[1]
                    item_d = str(r[col_d]).strip()
                    if item_d.lower() == 'nan': item_d = ""
                    loc = r.get('loc', 'SB??')
                    n_notam = r.get('n', '?')
                    raw_b = r.get('b', '')
                    raw_c = r.get('c', '') # Agora já deve vir corrigido do banco
                    
                    dt_b_obj = basic_parse(raw_b) or datetime.now()
                    dt_c_obj = basic_parse(raw_c) # Data final que está no banco

                    # Prepara para o parser
                    str_b_parser = dt_b_obj.strftime("%y%m%d%H%M")
                    str_c_parser = dt_c_obj.strftime("%y%m%d%H%M") if dt_c_obj else None
                    
                    status, detalhe = "N/A", "-"
                    try:
                        res = parser_notam.interpretar_periodo_atividade(item_d, loc, str_b_parser, str_c_parser)
                        if res:
                            status = "SUCESSO"
                            detalhe = f"{len(res)} períodos"
                        else:
                            status = "FALHA"
                            detalhe = "Vazio"
                    except Exception as e:
                        status = "ERRO"
                        detalhe = str(e)

                    resultados.append({
                        "LOC": loc, "NOTAM": n_notam, "Item D": item_d,
                        "Início (B)": dt_b_obj, "Fim (C)": dt_c_obj,
                        "Status": status, "Detalhe": detalhe
                    })
                
                st.session_state['auditoria_resultados'] = pd.DataFrame(resultados)
                st.session_state['force_load'] = False
                st.rerun()

    if 'auditoria_resultados' in st.session_state:
        df_res = st.session_state['auditoria_resultados']
        st.dataframe(df_res, use_container_width=True, height=600)