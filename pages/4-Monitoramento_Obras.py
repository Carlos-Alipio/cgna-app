import streamlit as st
import pandas as pd
from utils import db_manager, formatters, timeline_processor

st.set_page_config(page_title="Alertas Críticos", layout="wide")
st.title("🚨 Monitoramento Crítico")

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

st.divider()

# ==============================================================================
# 1. CARREGAR DADOS E REGRAS
# ==============================================================================
df_notams = db_manager.carregar_notams()
df_config = db_manager.carregar_filtros_configurados()

# Info de atualização
if not df_notams.empty:
    ultimo_dt = df_notams['dt'].max() if 'dt' in df_notams.columns else "-"
    data_fmt = formatters.formatar_data_notam(ultimo_dt)
    st.caption(f"📅 Dados baseados na última sincronização: **{data_fmt}**")
else:
    st.caption("Banco de dados vazio.")

# Carrega Regras Salvas
filtros_assunto = df_config[df_config['tipo'] == 'assunto']['valor'].tolist()
filtros_condicao = df_config[df_config['tipo'] == 'condicao']['valor'].tolist()

if not filtros_assunto or not filtros_condicao:
    st.warning("⚠️ Você ainda não configurou os filtros críticos.")
    st.info("Vá em **Configurações > Filtros Críticos** e selecione os assuntos e condições.")
    st.stop()

# ==============================================================================
# 2. APLICAR FILTRO LÓGICO (FROTA + ASSUNTO + CONDIÇÃO)
# ==============================================================================
if not df_notams.empty:
    
    # 1. Filtra Frota
    frota = db_manager.carregar_frota_monitorada()
    if frota:
        df_base = df_notams[df_notams['loc'].isin(frota)]
    else:
        df_base = df_notams

    # 2. Filtra Críticos (Assunto E Condição)
    mask_assunto = df_base['assunto_desc'].isin(filtros_assunto)
    mask_condicao = df_base['condicao_desc'].isin(filtros_condicao)
    
    df_critico = df_base[mask_assunto & mask_condicao].copy()
    
    # ==============================================================================
    # 3. INTERFACE DE ABAS
    # ==============================================================================
    
    tab_lista, tab_cronograma = st.tabs(["📋 Lista de NOTAMs", "📅 Cronograma de Restrições (Dias)"])

    # --------------------------------------------------------------------------
    # ABA 1: VISÃO GERAL (LISTA DE NOTAMS)
    # --------------------------------------------------------------------------
    with tab_lista:
        c1, c2 = st.columns([3, 1])
        
        if not df_critico.empty:
            c1.error(f"### 🎯 {len(df_critico)} NOTAMs Críticos Encontrados")
        else:
            c1.success("### ✅ Nenhuma ocorrência crítica no momento.")

        with c2.expander("Ver Regras Ativas"):
            st.write("**Assuntos:**", filtros_assunto)
            st.write("**Condições:**", filtros_condicao)

        st.markdown("---")

        if not df_critico.empty:
            # Ordenação
            if 'dt' in df_critico.columns:
                df_critico = df_critico.sort_values(by='dt', ascending=False)
                
            # Formatação
            df_critico['Início'] = df_critico['b'].apply(formatters.formatar_data_notam)
            df_critico['Fim'] = df_critico['c'].apply(formatters.formatar_data_notam)

            cols_view = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'Início', 'Fim', 'd', 'e']
            
            # Limpeza Visual (Remove 'None', 'nan' e nulos)
            df_exibicao = df_critico[cols_view].fillna("")
            for col in df_exibicao.columns:
                df_exibicao[col] = df_exibicao[col].astype(str).replace({'nan': '', 'None': '', 'NaT': ''})

            st.dataframe(
                df_exibicao,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "loc": "Local",
                    "n": "NOTAM",
                    "assunto_desc": "Assunto",
                    "condicao_desc": "Condição",
                    "d": "Período (Texto)",
                    "e": "Texto Completo"
                }
            )
            
            csv = df_exibicao.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Lista de NOTAMs (CSV)",
                data=csv,
                file_name="lista_notams_criticos.csv",
                mime="text/csv"
            )
        else:
            st.info("Com base nos seus filtros e na sua frota, a operação está normal.")

    # --------------------------------------------------------------------------
    # ABA 2: VISÃO DE CRONOGRAMA (DIAS ESPECÍFICOS)
    # --------------------------------------------------------------------------
    with tab_cronograma:
        st.markdown("### 🗓️ Dias Específicos de Fechamento/Restrição")
        st.caption("Esta tabela processa os textos complexos (DLY, EXC, SR-SS) e gera uma lista exata de datas e horários.")

        if not df_critico.empty:
            with st.spinner("Calculando calendário solar, feriados e intervalos..."):
                # Chama o processador inteligente
                df_dias = timeline_processor.gerar_cronograma_detalhado(df_critico)

            if not df_dias.empty:
                # Formatação visual (Datetime -> String bonita)
                df_view_dias = df_dias.copy()
                
                # Formata datas para o padrão brasileiro
                df_view_dias['Início'] = df_view_dias['Data Inicial'].dt.strftime('%d/%m/%Y %H:%M')
                df_view_dias['Fim'] = df_view_dias['Data Final'].dt.strftime('%d/%m/%Y %H:%M')
                
                # Calcula duração para facilitar análise
                df_view_dias['Duração'] = df_dias['Data Final'] - df_dias['Data Inicial']
                
                # Seleciona colunas finais
                cols_finais = ['Localidade', 'NOTAM', 'Assunto', 'Condição', 'Início', 'Fim', 'Duração']
                
                # Filtros rápidos na tabela
                st.dataframe(
                    df_view_dias[cols_finais],
                    use_container_width=True,
                    hide_index=True,
                    height=600
                )
                
                # Botão de Download do Relatório Processado
                csv_dias = df_view_dias[cols_finais].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar Relatório de Dias (CSV)",
                    data=csv_dias,
                    file_name="cronograma_restricoes_detalhado.csv",
                    mime="text/csv",
                    type="primary",
                    help="Baixa a lista explodida dia a dia, ideal para Excel."
                )
            else:
                st.warning("Não foi possível extrair datas específicas dos NOTAMs listados (verifique se possuem período válido).")
        else:
            st.info("Sem dados críticos para gerar cronograma.")

else:
    st.info("Banco vazio. Vá ao 'Painel de Notams' para atualizar os dados.")