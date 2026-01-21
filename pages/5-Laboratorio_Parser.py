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
# ABA 2: AUDITORIA DO BANCO DE DADOS (CORRIGIDA)
# ==============================================================================
with tab_banco:
    st.subheader("🕵️ Auditoria: Supabase")
    st.markdown("Verificação de NOTAMs com Item D, corrigindo datas brutas do banco.")

    if st.button("🔄 Carregar do Banco", type="primary"):
        with st.spinner("Carregando e processando datas..."):
            df_full = db_manager.carregar_notams()
            
            if df_full.empty:
                st.warning("Banco vazio.")
                st.stop()
            
            # Filtra apenas quem tem Item D
            col_d = 'd'
            if col_d not in df_full.columns:
                st.error("Coluna 'd' não encontrada.")
                st.stop()

            df_analise = df_full[df_full[col_d].notna() & (df_full[col_d].astype(str).str.strip() != '')].copy()
            df_analise = df_analise[~df_analise[col_d].astype(str).str.upper().isin(["NIL", "NONE"])]

            total = len(df_analise)
            st.success(f"Analisando {total} registros...")
            
            progress_bar = st.progress(0)
            resultados = []

            # --- FUNÇÃO DE CORREÇÃO DE DATA ---
            def parse_db_date(val):
                """
                Força a interpretação correta do formato NOTAM (YYMMDDHHMM)
                mesmo que o banco traga como número ou string.
                """
                val_str = str(val).strip()
                # Remove pontuação se houver (ex: 25-12...)
                val_clean = val_str.replace("-", "").replace(":", "").replace(" ", "")
                
                # Se for formato YYMMDDHHMM (10 digitos)
                if len(val_clean) == 10 and val_clean.isdigit():
                    return val_clean # Retorna string limpa para o parser usar
                
                # Se for timestamp do pandas, converte
                if isinstance(val, (datetime, pd.Timestamp)):
                    return val.strftime("%y%m%d%H%M")
                    
                return "2601010000" # Fallback seguro (2026) se falhar

            # --- LOOP DE ANÁLISE ---
            for idx, row in enumerate(df_analise.iterrows()):
                r = row[1]
                
                # Barra de progresso otimizada
                if idx % 50 == 0:
                    progress_bar.progress(min((idx + 1) / total, 1.0))
                
                item_d = str(r[col_d]).strip()
                loc = r.get('loc', 'SB??')
                n_notam = r.get('n', '?')
                
                # Pega valores brutos do banco
                raw_b = r.get('b', '')
                raw_c = r.get('c', '')
                
                # Sanitiza para o formato que o parser entende (YYMMDDHHMM)
                str_b = parse_db_date(raw_b)
                str_c = parse_db_date(raw_c)
                
                status = "N/A"
                detalhe = "-"
                
                try:
                    res = parser_notam.interpretar_periodo_atividade(item_d, loc, str_b, str_c)
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
                
                # Tenta converter para datetime real APENAS para exibição na tabela (Visual)
                try:
                    view_b = datetime.strptime(str_b, "%y%m%d%H%M")
                except: view_b = None
                
                try:
                    view_c = datetime.strptime(str_c, "%y%m%d%H%M")
                except: view_c = None

                resultados.append({
                    "LOC": loc,
                    "NOTAM": n_notam,
                    "Item D": item_d,
                    "Início (B)": view_b, # Objeto datetime para a coluna ficar bonita
                    "Fim (C)": view_c,
                    "Status": status,
                    "Detalhe": detalhe
                })
            
            progress_bar.progress(100)
            
            # --- EXIBIÇÃO ---
            df_res = pd.DataFrame(resultados)
            
            st.divider()
            
            k1, k2, k3 = st.columns(3)
            falhas = df_res[df_res['Status'].isin(['FALHA', 'ERRO CÓDIGO'])]
            sucessos = df_res[df_res['Status'] == 'SUCESSO']
            
            k1.metric("Total", total)
            k2.metric("Sucessos", len(sucessos))
            k3.metric("Falhas", len(falhas), delta_color="inverse")
            
            filtro = st.radio("Visualizar:", ["🚨 Apenas Falhas", "✅ Apenas Sucessos", "📄 Tudo"], horizontal=True)
            
            if filtro == "🚨 Apenas Falhas":
                df_show = falhas
            elif filtro == "✅ Apenas Sucessos":
                df_show = sucessos
            else:
                df_show = df_res
            
            st.dataframe(
                df_show,
                use_container_width=True,
                column_config={
                    "Item D": st.column_config.TextColumn("Texto (Item D)", width="large"),
                    "Início (B)": st.column_config.DatetimeColumn("Vigência Ini", format="DD/MM/YYYY HH:mm"),
                    "Fim (C)": st.column_config.DatetimeColumn("Vigência Fim", format="DD/MM/YYYY HH:mm"),
                },
                height=600
            )