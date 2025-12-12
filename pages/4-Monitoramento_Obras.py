import streamlit as st
import pandas as pd
from datetime import datetime, date
from utils import db_manager, formatters, timeline_processor, pdf_generator

st.set_page_config(page_title="Alertas Críticos", layout="wide")
st.title("🚨 Monitoramento Crítico")

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

st.divider()

# ==============================================================================
# 1. CARREGAMENTO DE DADOS
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
# 2. PROCESSAMENTO (FILTRO LÓGICO)
# ==============================================================================
df_critico = pd.DataFrame()

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
tab_lista, tab_cronograma, tab_turno = st.tabs(["📋 Lista de NOTAMs", "📅 Cronograma Geral", "👮 Relatório de Turno"])

# --------------------------------------------------------------------------
# ABA 1: VISÃO GERAL (LISTA DE NOTAMS)
# --------------------------------------------------------------------------
with tab_lista:
    if not df_critico.empty:
        c1, c2 = st.columns([3, 1])
        c1.error(f"### 🎯 {len(df_critico)} NOTAMs Críticos")
        
        with c2.expander("Ver Regras Ativas"):
            st.write("**Assuntos:**", filtros_assunto)
            st.write("**Condições:**", filtros_condicao)

        df_exibicao = df_critico.copy()
        df_exibicao['Início'] = df_exibicao['b'].apply(formatters.formatar_data_notam)
        df_exibicao['Fim'] = df_exibicao['c'].apply(formatters.formatar_data_notam)
        
        # Limpeza Visual
        cols_view = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'Início', 'Fim', 'd', 'e']
        df_show = df_exibicao[cols_view].fillna("")
        for col in df_show.columns:
            df_show[col] = df_show[col].astype(str).replace({'nan': '', 'None': '', 'NaT': ''})

        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "loc": "Local", "n": "NOTAM", "assunto_desc": "Assunto",
                "condicao_desc": "Condição", "d": "Período (Texto)", "e": "Texto Completo"
            }
        )
        
        csv = df_show.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Lista (CSV)", data=csv, file_name="lista_critica.csv", mime="text/csv")
    else:
        st.info("Sem dados críticos no momento.")

# --------------------------------------------------------------------------
# ABA 2: CRONOGRAMA (COM FILTROS)
# --------------------------------------------------------------------------
with tab_cronograma:
    if not df_critico.empty:
        with st.spinner("Calculando cronograma detalhado..."):
            df_dias = timeline_processor.gerar_cronograma_detalhado(df_critico)
        
        if not df_dias.empty:
            df_view = df_dias.copy()
            df_view['Início'] = df_view['Data Inicial'].dt.strftime('%d/%m/%Y %H:%M')
            df_view['Fim'] = df_view['Data Final'].dt.strftime('%d/%m/%Y %H:%M')
            
            # --- ÁREA DE FILTROS ---
            st.markdown("##### 🔍 Filtros Dinâmicos")
            col_f1, col_f2 = st.columns(2)
            
            locs_disponiveis = sorted(df_view['Localidade'].unique())
            with col_f1:
                filtro_loc = st.multiselect("Filtrar por Localidade:", locs_disponiveis)
            
            # Filtro NOTAM reativo
            if filtro_loc:
                notams_disponiveis = sorted(df_view[df_view['Localidade'].isin(filtro_loc)]['NOTAM'].unique())
            else:
                notams_disponiveis = sorted(df_view['NOTAM'].unique())
                
            with col_f2:
                filtro_notam = st.multiselect("Filtrar por Número do NOTAM:", notams_disponiveis)

            # Aplicação
            if filtro_loc: df_view = df_view[df_view['Localidade'].isin(filtro_loc)]
            if filtro_notam: df_view = df_view[df_view['NOTAM'].isin(filtro_notam)]

            st.markdown(f"**Exibindo {len(df_view)} registros**")
            
            st.dataframe(
                df_view[['Localidade', 'NOTAM', 'Assunto', 'Condição', 'Início', 'Fim', 'Texto']],
                use_container_width=True,
                height=500,
                column_config={"Texto": st.column_config.TextColumn("Texto (e)", width="large")}
            )
            
            csv_dias = df_view.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Cronograma Filtrado (CSV)", data=csv_dias, file_name="cronograma.csv", mime="text/csv")
        else:
            st.warning("Não foi possível gerar datas específicas.")
    else:
        st.info("Sem dados.")

# --------------------------------------------------------------------------
# ABA 3: RELATÓRIO DE TURNO (CORRIGIDA)
# --------------------------------------------------------------------------
with tab_turno:
    st.markdown("### 👮 Visão Operacional por Turno")
    
    c_data, c_turno, c_void = st.columns([2, 2, 1])
    
    with c_data:
        # CORREÇÃO: ID ÚNICO + FORMATO BR
        data_selecionada = st.date_input(
            "Data de Referência", 
            value=date.today(), 
            format="DD/MM/YYYY",
            key="dt_ref_turno_input" 
        )

    with c_turno:
        # CORREÇÃO: ID ÚNICO + NOVOS HORÁRIOS UTC
        opcao_turno = st.selectbox(
            "Selecione o Turno", 
            [
                "MADRUGADA (03h-15h UTC)", 
                "MANHA (09h-21h UTC)", 
                "TARDE (15h-03h UTC)", 
                "NOITE (21h-09h UTC)"
            ],
            key="sel_turno_input"
        )
        chave_turno = opcao_turno.split()[0] 

    if not df_critico.empty:
        # Gera e Filtra
        df_timeline_full = timeline_processor.gerar_cronograma_detalhado(df_critico)
        df_turno_result, texto_periodo = timeline_processor.filtrar_por_turno(df_timeline_full, data_selecionada, chave_turno)

        st.markdown("---")
        
        if not df_turno_result.empty:
            st.info(f"### 🕒 Turno: {texto_periodo}")
            
            df_view = df_turno_result.copy()
            df_view['Início Restrição'] = df_view['Data Inicial'].dt.strftime('%d/%m/%Y %H:%M')
            df_view['Fim Restrição'] = df_view['Data Final'].dt.strftime('%d/%m/%Y %H:%M')
            
            cols_show = ['Localidade', 'NOTAM', 'Assunto', 'Condição', 'Início Restrição', 'Fim Restrição', 'Texto']
            
            st.dataframe(
                df_view[cols_show],
                use_container_width=True,
                hide_index=True,
                height=500,
                column_config={"Texto": st.column_config.TextColumn("Texto (e)", width="large")}
            )
            
            # --- ÁREA DE AÇÃO ---
            col_pdf, col_copy = st.columns([1, 2])
            
            with col_pdf:
                st.write("#### 📤 Exportar")
                
                # Gera PDF
                pdf_bytes = pdf_generator.gerar_pdf_turno(
                    df_view, 
                    chave_turno, 
                    data_selecionada.strftime('%d/%m/%Y')
                )
                
                nome_arq = f"Relatorio_Turno_{chave_turno}_{data_selecionada.strftime('%d%m%Y')}.pdf"
                
                st.download_button(
                    label="📄 Baixar PDF (Layout CONA)",
                    data=pdf_bytes,
                    file_name=nome_arq,
                    mime="application/pdf",
                    type="primary",
                    key="btn_down_pdf"
                )

            with col_copy:
                with st.expander("📋 Texto para Passagem de Serviço (Copia e Cola)"):
                    texto_report = f"*PASSAGEM DE SERVIÇO - {chave_turno} ({data_selecionada.strftime('%d/%m/%Y')})*\n\n"
                    for idx, row in df_view.iterrows():
                        texto_report += f"📍 *{row['Localidade']}* - {row['Assunto']}\n"
                        texto_report += f"   NOTAM: {row['NOTAM']}\n"
                        texto_report += f"   Vigência: {row['Início Restrição']}z até {row['Fim Restrição']}z\n"
                        texto_report += f"   Obs: {row['Texto'][:150]}...\n\n"
                    
                    st.text_area("Texto", value=texto_report, height=200, label_visibility="collapsed", key="txt_area_servico")

        else:
            st.success(f"✅ Nenhuma restrição crítica prevista para o turno da {chave_turno}.")
    else:
        st.warning("Sem dados críticos carregados.")