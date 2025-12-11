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
# CARREGAMENTO (Igual ao anterior)
# ==============================================================================
df_notams = db_manager.carregar_notams()
df_config = db_manager.carregar_filtros_configurados()

filtros_assunto = df_config[df_config['tipo'] == 'assunto']['valor'].tolist()
filtros_condicao = df_config[df_config['tipo'] == 'condicao']['valor'].tolist()

if not filtros_assunto or not filtros_condicao:
    st.warning("Filtros não configurados.")
    st.stop()

# ==============================================================================
# PROCESSAMENTO DOS DADOS CRÍTICOS
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
# Adicionamos a aba "Relatório de Turno"
tab_lista, tab_cronograma, tab_turno = st.tabs(["📋 Lista de NOTAMs", "📅 Cronograma Geral", "👮 Relatório de Turno"])

# --- ABA 1 E 2 (MANTENHA O CÓDIGO ANTERIOR AQUI SE QUISER) ---
# Vou focar no código novo da Aba 3 para economizar espaço, mas o arquivo
# final deve conter as abas anteriores.

# ... (Código da tab_lista e tab_cronograma igual à versão V24) ...
with tab_lista:
    # (Seu código existente da aba 1...)
    if df_critico.empty:
        st.info("Sem dados críticos.")
    else:
        st.dataframe(df_critico[['loc', 'n', 'assunto_desc', 'd', 'e']], use_container_width=True)

with tab_cronograma:
    # (Seu código existente da aba 2...)
    if not df_critico.empty:
        df_dias_full = timeline_processor.gerar_cronograma_detalhado(df_critico)
        st.dataframe(df_dias_full, use_container_width=True)

# --------------------------------------------------------------------------
# ABA 3: RELATÓRIO DE TURNO (NOVIDADE)
# --------------------------------------------------------------------------
with tab_turno:
    st.markdown("### 👮 Visão Operacional por Turno")
    st.caption("Filtra ocorrências que impactam as próximas 12h a partir do início do turno.")

    # Controles de Filtro
    c_data, c_turno, c_btn = st.columns([2, 2, 1])
    
    with c_data:
        data_selecionada = st.date_input("Data de Referência", value=date.today())
    
    with c_turno:
        opcao_turno = st.selectbox(
            "Selecione o Turno",
            ["MADRUGADA (00h-12h)", "MANHA (06h-18h)", "TARDE (12h-00h)", "NOITE (18h-06h)"]
        )
        # Extrai a chave simples para a função (ex: "MANHA")
        chave_turno = opcao_turno.split()[0] 

    # Botão de Processar
    if not df_critico.empty:
        # Pré-calcula a timeline completa (se já não foi calculada na aba 2)
        # Idealmente usamos cache, mas aqui chamamos direto
        df_timeline_full = timeline_processor.gerar_cronograma_detalhado(df_critico)
        
        df_turno_result, texto_periodo = timeline_processor.filtrar_por_turno(
            df_timeline_full, 
            data_selecionada, 
            chave_turno
        )

        st.markdown("---")
        
        if not df_turno_result.empty:
            st.info(f"### 🕒 Periodo do Turno: {texto_periodo}")
            st.markdown(f"**{len(df_turno_result)}** restrições encontradas neste range de 12 horas.")

            # Formatação para exibição
            df_view = df_turno_result.copy()
            
            # Formata datas
            df_view['Início Restrição'] = df_view['Data Inicial'].dt.strftime('%d/%m %H:%M')
            df_view['Fim Restrição'] = df_view['Data Final'].dt.strftime('%d/%m %H:%M')
            
            # Duração (HH:MM)
            def fmt_dur(r):
                secs = int((r['Data Final'] - r['Data Inicial']).total_seconds())
                return f"{secs//3600:02d}:{(secs%3600)//60:02d}"
            df_view['Duração Total'] = df_view.apply(fmt_dur, axis=1)

            # Mostra Tabela
            cols_show = ['Localidade', 'NOTAM', 'Assunto', 'Condição', 'Início Restrição', 'Fim Restrição', 'Duração Total']
            st.dataframe(
                df_view[cols_show],
                use_container_width=True,
                hide_index=True,
                height=500
            )
            
            # Geração de Relatório de Texto (Para Copiar e Colar em E-mail/Zap)
            with st.expander("📋 Texto para Passagem de Serviço (Copiar/Colar)"):
                texto_report = f"*RELATÓRIO DE IMPACTO DE PISTA - TURNO {chave_turno}*\n"
                texto_report += f"Referência: {texto_periodo}\n\n"
                
                for idx, row in df_view.iterrows():
                    texto_report += f"✈️ *{row['Localidade']}*: {row['Assunto']} {row['Condição']}\n"
                    texto_report += f"   NOTAM: {row['NOTAM']}\n"
                    texto_report += f"   Horário: {row['Início Restrição']} até {row['Fim Restrição']}\n"
                    texto_report += "   --------------------------------\n"
                
                st.text_area("Texto", value=texto_report, height=300)

        else:
            st.success(f"✅ Nenhuma restrição crítica prevista para o turno da **{chave_turno}** ({texto_periodo}).")
    else:
        st.warning("Sem dados críticos carregados.")