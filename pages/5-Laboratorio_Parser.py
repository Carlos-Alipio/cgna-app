import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import parser_notam, db_manager

st.set_page_config(page_title="Lab Parser Item D", layout="wide")
st.title("🛠️ Laboratório de Testes: Parser NOTAM")
st.markdown("Ferramenta para validação do algoritmo usando dados reais do **Banco de Dados (Supabase)**.")

tab_manual, tab_banco = st.tabs(["🧪 Teste Manual", "💾 Auditoria do Banco de Dados"])

# ==============================================================================
# ABA 1: TESTE MANUAL (MANTIDA IGUAL - ÓTIMA PARA DEBUG RÁPIDO)
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
# ABA 2: AUDITORIA DO BANCO DE DADOS
# ==============================================================================
with tab_banco:
    st.subheader("🕵️ Auditoria: Supabase")
    st.markdown("Esta aba carrega todos os NOTAMs salvos no seu banco e verifica quais têm Item D problemático.")

    col_btn, col_info = st.columns([1, 3])
    
    with col_btn:
        btn_carregar = st.button("🔄 Carregar do Banco", type="primary")

    if btn_carregar:
        with st.spinner("Carregando dados do Supabase..."):
            # 1. Carrega DataFrame Bruto do Banco
            df_full = db_manager.carregar_notams()
            
            if df_full.empty:
                st.warning("O banco de dados está vazio ou não foi possível conectar.")
                st.stop()
            
            # Verifica se a coluna 'd' existe (Item D)
            col_d = 'd' # Ajuste se no seu banco for outro nome, mas o padrão do db_manager é 'd'
            if col_d not in df_full.columns:
                st.error(f"Coluna '{col_d}' não encontrada no DataFrame. Colunas disponíveis: {list(df_full.columns)}")
                st.stop()

            # 2. Filtra apenas quem tem Item D preenchido
            # Remove nulos, NaNs e strings vazias ou só com espaços
            df_analise = df_full[df_full[col_d].notna() & (df_full[col_d].astype(str).str.strip() != '')].copy()
            
            # Remove falsos positivos (NIL, NONE)
            df_analise = df_analise[~df_analise[col_d].astype(str).str.upper().isin(["NIL", "NONE"])]

            total_analise = len(df_analise)
            
            if total_analise == 0:
                st.info("Nenhum NOTAM com Item D (restrição de horário) encontrado no banco.")
                st.stop()
            
        st.success(f"Analisando {total_analise} NOTAMs com restrição de horário...")
        progress_bar = st.progress(0)
        
        resultados = []
        
        # Helper para garantir formato de data para o parser (YYMMDDHHMM)
        def format_date_for_parser(val):
            # O db_manager geralmente retorna datetime objects.
            # O parser aceita string YYMMDDHHMM.
            try:
                if isinstance(val, (datetime, pd.Timestamp)):
                    return val.strftime("%y%m%d%H%M")
                return str(val) # Tenta passar string se não for data
            except:
                return "2501010000" # Fallback

        # 3. Loop de Análise
        for idx, row in enumerate(df_analise.iterrows()):
            # row é uma tupla (index, series)
            r = row[1]
            
            # Atualiza barra
            if idx % 50 == 0:
                progress_bar.progress(min((idx + 1) / total_analise, 1.0))
            
            # Dados
            item_d_text = str(r[col_d]).strip()
            loc = r.get('loc', 'SB??')
            n_notam = r.get('n', '?')
            val_b = r.get('b', None)
            val_c = r.get('c', None)
            
            # Prepara argumentos
            str_b = format_date_for_parser(val_b)
            str_c = format_date_for_parser(val_c)
            
            status = "N/A"
            res_visual = "-"
            
            try:
                # O GRANDE TESTE
                res = parser_notam.interpretar_periodo_atividade(item_d_text, loc, str_b, str_c)
                
                if res:
                    status = "SUCESSO"
                    # Resumo visual: "3 dias (10/01, 11/01...)"
                    dias_str = ", ".join([d['inicio'].strftime('%d/%m') for d in res[:3]])
                    if len(res) > 3: dias_str += "..."
                    res_visual = f"{len(res)} dias ({dias_str})"
                else:
                    status = "FALHA"
                    res_visual = "Retorno Vazio []"
            except Exception as e:
                status = "ERRO CÓDIGO"
                res_visual = str(e)
            
            resultados.append({
                "LOC": loc,
                "NOTAM": n_notam,
                "Item D": item_d_text,
                "Início (B)": val_b,
                "Fim (C)": val_c,
                "Status": status,
                "Detalhe": res_visual
            })
            
        progress_bar.progress(100)
        
        # 4. Exibição dos Resultados
        df_res = pd.DataFrame(resultados)
        
        st.divider()
        
        # Métricas
        falhas = df_res[df_res['Status'].isin(['FALHA', 'ERRO CÓDIGO'])]
        sucessos = df_res[df_res['Status'] == 'SUCESSO']
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Analisado", total_analise)
        k2.metric("✅ Sucessos", len(sucessos))
        k3.metric("🚨 Falhas", len(falhas), delta_color="inverse")
        
        # Filtros de Visualização
        filtro = st.radio("Visualizar:", ["🚨 Apenas Falhas", "✅ Apenas Sucessos", "📄 Tudo"], horizontal=True)
        
        if filtro == "🚨 Apenas Falhas":
            df_show = falhas
            # Agrupar erros idênticos
            if not df_show.empty and st.checkbox("Agrupar Textos Idênticos (Remover Duplicatas)", value=True):
                 df_show = df_show.drop_duplicates(subset=['Item D'])
        elif filtro == "✅ Apenas Sucessos":
            df_show = sucessos
        else:
            df_show = df_res
            
        # Tabela Final
        st.dataframe(
            df_show,
            use_container_width=True,
            column_config={
                "Item D": st.column_config.TextColumn("Texto (Item D)", width="large"),
                "Detalhe": st.column_config.TextColumn("Resultado do Robô", width="medium"),
                "Início (B)": st.column_config.DatetimeColumn("Vigência Ini", format="DD/MM/YYYY HH:mm"),
                "Fim (C)": st.column_config.DatetimeColumn("Vigência Fim", format="DD/MM/YYYY HH:mm"),
            },
            height=600
        )
        
        # Download
        csv = df_show.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Baixar Relatório (CSV)",
            data=csv,
            file_name="auditoria_parser_banco.csv",
            mime="text/csv"
        )