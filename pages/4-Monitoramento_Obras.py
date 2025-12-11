import streamlit as st
import pandas as pd
from datetime import datetime, date
from utils import db_manager, formatters, timeline_processor

st.set_page_config(page_title="Alertas Críticos", layout="wide")
st.title("🚨 Monitoramento Crítico")

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

st.divider()

# ==============================================================================
# CARREGAMENTO
# ==============================================================================
df_notams = db_manager.carregar_notams()
df_config = db_manager.carregar_filtros_configurados()

if not df_notams.empty:
    ultimo_dt = df_notams['dt'].max() if 'dt' in df_notams.columns else "-"
    data_fmt = formatters.formatar_data_notam(ultimo_dt)
    st.caption(f"📅 Dados baseados na última sincronização: **{data_fmt}**")

filtros_assunto = df_config[df_config['tipo'] == 'assunto']['valor'].tolist()
filtros_condicao = df_config[df_config['tipo'] == 'condicao']['valor'].tolist()

if not filtros_assunto or not filtros_condicao:
    st.warning("Filtros não configurados.")
    st.stop()

# ==============================================================================
# PROCESSAMENTO
# ==============================================================================
df_critico = pd.DataFrame()
if not df_notams.empty:
    frota = db_manager.carregar_frota_monitorada()
    if frota:
        df_base = df_notams[df_notams['loc'].isin(frota)]
    else:
        df_base = df_notams

    mask_assunto = df_base['assunto_desc'].isin(filtros_assunto)
    mask_condicao = df_base['condicao_desc'].isin(filtros_condicao)
    df_critico = df_base[mask_assunto & mask_condicao].copy()

# ==============================================================================
# INTERFACE DE ABAS
# ==============================================================================
tab_lista, tab_cronograma, tab_turno = st.tabs(["📋 Lista de NOTAMs", "📅 Cronograma Geral", "👮 Relatório de Turno"])

# --- ABA 1: LISTA ---
with tab_lista:
    if not df_critico.empty:
        c1, c2 = st.columns([3, 1])
        c1.error(f"### 🎯 {len(df_critico)} NOTAMs Críticos")
        
        df_exibicao = df_critico.copy()
        df_exibicao['Início'] = df_exibicao['b'].apply(formatters.formatar_data_notam)
        df_exibicao['Fim'] = df_exibicao['c'].apply(formatters.formatar_data_notam)
        
        st.dataframe(
            df_exibicao[['loc', 'n', 'assunto_desc', 'condicao_desc', 'Início', 'Fim', 'd', 'e']],
            use_container_width=True,
            column_config={"e": "Texto Completo"}
        )
    else:
        st.info("Sem dados críticos.")

# --- ABA 2: CRONOGRAMA ---
with tab_cronograma:
    if not df_critico.empty:
        with st.spinner("Gerando cronograma..."):
            df_dias = timeline_processor.gerar_cronograma_detalhado(df_critico)
        
        if not df_dias.empty:
            df_view = df_dias.copy()
            df_view['Início'] = df_view['Data Inicial'].dt.strftime('%d/%m/%Y %H:%M')
            df_view['Fim'] = df_view['Data Final'].dt.strftime('%d/%m/%Y %H:%M')
            
            st.dataframe(
                df_view[['Localidade', 'NOTAM', 'Assunto', 'Condição', 'Início', 'Fim', 'Texto']],
                use_container_width=True,
                height=500,
                column_config={"Texto": st.column_config.TextColumn("Texto (e)", width="large")}
            )
    else:
        st.info("Sem dados.")

# --------------------------------------------------------------------------
# ABA 3: RELATÓRIO DE TURNO (ATUALIZADA)
# --------------------------------------------------------------------------
with tab_turno:
    st.markdown("### 👮 Visão Operacional por Turno")
    
    c_data, c_turno, c_void = st.columns([2, 2, 1])
    with c_data:
        data_selecionada = st.date_input("Data de Referência", value=date.today())
    with c_turno:
        opcao_turno = st.selectbox("Selecione o Turno", ["MADRUGADA (00h-12h)", "MANHA (06h-18h)", "TARDE (12h-00h)", "NOITE (18h-06h)"])
        chave_turno = opcao_turno.split()[0] 

    if not df_critico.empty:
        df_timeline_full = timeline_processor.gerar_cronograma_detalhado(df_critico)
        df_turno_result, texto_periodo = timeline_processor.filtrar_por_turno(df_timeline_full, data_selecionada, chave_turno)

        st.markdown("---")
        
        if not df_turno_result.empty:
            st.info(f"### 🕒 Turno: {texto_periodo}")
            
            df_view = df_turno_result.copy()
            df_view['Início Restrição'] = df_view['Data Inicial'].dt.strftime('%d/%m %H:%M')
            df_view['Fim Restrição'] = df_view['Data Final'].dt.strftime('%d/%m %H:%M')
            
            # --- MUDANÇA: Exibe Texto (e) em vez de Duração ---
            cols_show = ['Localidade', 'NOTAM', 'Assunto', 'Condição', 'Início Restrição', 'Fim Restrição', 'Texto']
            
            st.dataframe(
                df_view[cols_show],
                use_container_width=True,
                hide_index=True,
                height=500,
                column_config={
                    "Texto": st.column_config.TextColumn("Texto (e)", width="large") # Coluna larga para leitura
                }
            )
            
            # Texto para Copiar
            with st.expander("📋 Texto para Passagem de Serviço"):
                texto_report = f"*PASSAGEM DE SERVIÇO - {chave_turno} ({data_selecionada.strftime('%d/%m')})*\n\n"
                for idx, row in df_view.iterrows():
                    texto_report += f"📍 *{row['Localidade']}* - {row['Assunto']}\n"
                    texto_report += f"   NOTAM: {row['NOTAM']}\n"
                    texto_report += f"   Vigência no Turno: {row['Início Restrição']}z até {row['Fim Restrição']}z\n"
                    texto_report += f"   Detalhe: {row['Texto'][:100]}...\n\n" # Corta texto muito longo
                st.text_area("Copiar", value=texto_report, height=300)

        else:
            st.success(f"✅ Nenhuma restrição crítica prevista para este turno.")
    else:
        st.warning("Sem dados críticos carregados.")