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
        # Campo aberto para testar PERM
        str_c_manual = st.text_input("Fim (Item C)", value=(dt_hoje + timedelta(days=30)).strftime("%y%m%d")+"2359", help="Digite uma data YYMMDDHHMM ou 'PERM'")
        str_b = dt_b.strftime("%y%m%d") + "0000"
        
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
        # Permite Item D vazio para testar PERM continuo
        try:
            res = parser_notam.interpretar_periodo_atividade(item_d_input, "SBGR", str_b, str_c_manual)
            if not res:
                st.warning("⚠️ Retorno vazio (pode ser erro ou fora da vigência).")
            else:
                df_res = pd.DataFrame(res)
                df_res['Dia'] = df_res['inicio'].dt.strftime('%d/%m/%Y (%a)')
                df_res['Hora'] = df_res['inicio'].dt.strftime('%H:%M') + " - " + df_res['fim'].dt.strftime('%H:%M')
                st.success(f"✅ Identificados {len(df_res)} períodos.")
                st.dataframe(df_res[['Dia', 'Hora']], use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")

# ==============================================================================
# ABA 2: AUDITORIA DO BANCO DE DADOS
# ==============================================================================
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

            # Mantém linhas para análise
            df_analise = df_full.copy()
            df_analise = df_analise[~df_analise[col_d].astype(str).str.upper().isin(["NIL", "NONE"])]

            total = len(df_analise)
            progress_bar = st.progress(0)
            resultados = []

            # Função auxiliar apenas para formatação visual inicial da tabela
            def format_date_visual(val):
                s = str(val).strip()
                if "PERM" in s.upper(): return "PERM"
                try:
                     clean = s.replace("-", "").replace(":", "").replace(" ", "")
                     if len(clean) == 10: return datetime.strptime(clean, "%y%m%d%H%M")
                     if isinstance(val, (datetime, pd.Timestamp)): return val
                except: pass
                return s

            for idx, row in enumerate(df_analise.iterrows()):
                r = row[1]
                if idx % 50 == 0: progress_bar.progress(min((idx + 1) / total, 1.0))
                
                item_d = str(r[col_d]).strip()
                if item_d.lower() == 'nan': item_d = ""
                
                loc = r.get('loc', 'SB??')
                n_notam = r.get('n', '?')
                
                # Pega valores CRUS do banco
                raw_b = r.get('b', '')
                raw_c = r.get('c', '') # Passa o valor cru (que pode ter PERM)
                
                status = "N/A"
                detalhe = "-"
                view_c = format_date_visual(raw_c) # Visual original
                view_b = format_date_visual(raw_b)
                
                try:
                    # Chama o parser com o valor cru de C
                    res = parser_notam.interpretar_periodo_atividade(item_d, loc, raw_b, raw_c)
                    if res:
                        status = "SUCESSO"
                        dias_str = ", ".join([d['inicio'].strftime('%d/%m') for d in res[:3]])
                        if len(res) > 3: dias_str += "..."
                        detalhe = f"{len(res)} dias ({dias_str})"
                        
                        # Se funcionou, atualiza a visualização do Fim C para refletir o cálculo real
                        view_c = res[-1]['fim'] 
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
                    "Início (B)": view_b,
                    "Fim (C)": view_c,
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
                "Fim (C)": st.column_config.DatetimeColumn("Vigência Fim (Real)", format="DD/MM/YYYY HH:mm"),
            },
            height=600
        )