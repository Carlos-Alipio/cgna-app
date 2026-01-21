import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import parser_notam, db_manager

st.set_page_config(page_title="Lab Parser Item D", layout="wide")
st.title("🛠️ Laboratório de Testes: Parser NOTAM")
st.markdown("Ferramenta para validação do algoritmo usando dados reais do **Banco de Dados (Supabase)**.")

tab_manual, tab_banco = st.tabs(["🧪 Teste Manual", "💾 Auditoria do Banco de Dados"])

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

with tab_banco:
    st.subheader("🕵️ Auditoria: Supabase")
    
    if st.button("🔄 Carregar/Atualizar Dados do Banco", type="primary"):
        with st.spinner("Carregando e processando datas..."):
            df_full = db_manager.carregar_notams()
            
            if df_full.empty:
                st.warning("Banco vazio.")
                st.stop()
            
            col_d = 'd'
            if col_d not in df_full.columns:
                st.error("Coluna 'd' não encontrada.")
                st.stop()

            df_analise = df_full.copy()
            df_analise = df_analise[~df_analise[col_d].astype(str).str.upper().isin(["NIL", "NONE"])]

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

                dt_b_obj = basic_parse(raw_b)
                if not dt_b_obj: dt_b_obj = datetime.now()
                
                dt_c_obj = basic_parse(raw_c)

                # CORREÇÃO NA LEITURA (SIMULAÇÃO): SE PERM EM C -> 365 DIAS
                is_perm_raw = "PERM" in str(raw_c).upper()
                
                dt_c_final = dt_c_obj
                if is_perm_raw:
                    dt_c_final = dt_b_obj + timedelta(days=365)

                str_b_parser = dt_b_obj.strftime("%y%m%d%H%M")
                str_c_parser = dt_c_final.strftime("%y%m%d%H%M") if dt_c_final else None
                
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
                    "Fim (C)": dt_c_final,
                    "Status": status,
                    "Detalhe": detalhe
                })
            
            progress_bar.progress(100)
            st.session_state['auditoria_resultados'] = pd.DataFrame(resultados)
            st.rerun()

    if 'auditoria_resultados' in st.session_state:
        df_res = st.session_state['auditoria_resultados']
        
        st.divider()
        
        falhas = df_res[df_res['Status'].isin(['FALHA', 'ERRO CÓDIGO'])]
        sucessos = df_res[df_res['Status'] == 'SUCESSO']
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Total", len(df_res))
        k2.metric("Sucessos", len(sucessos))
        k3.metric("Falhas", len(falhas), delta_color="inverse")
        
        filtro = st.radio("Visualizar:", ["🚨 Apenas Falhas", "✅ Apenas Sucessos", "📄 Tudo"], horizontal=True, index=2)
        
        if filtro == "🚨 Apenas Falhas": df_show = falhas
        elif filtro == "✅ Apenas Sucessos": df_show = sucessos
        else: df_show = df_res
        
        st.dataframe(
            df_show,
            use_container_width=True,
            column_config={
                "Item D": st.column_config.TextColumn("Texto (Item D)", width="large"),
                "Detalhe": st.column_config.TextColumn("Resultado do Robô", width="medium"),
                "Início (B)": st.column_config.DatetimeColumn("Vigência Ini", format="DD/MM/YYYY HH:mm"),
                "Fim (C)": st.column_config.DatetimeColumn("Vigência Fim (C)", format="DD/MM/YYYY HH:mm"),
            },
            height=600
        )