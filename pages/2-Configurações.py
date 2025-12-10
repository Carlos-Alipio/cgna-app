import streamlit as st
import pandas as pd
from sqlalchemy import text
from utils import db_manager
# Importamos os dicionários para ter as opções para escolher
from utils.notam_codes import NOTAM_SUBJECT, NOTAM_CONDITION 

st.set_page_config(page_title="Configurações", layout="wide")
st.title("⚙️ Configurações do Sistema")

if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

tab1, tab2 = st.tabs(["✈️ Frota (ICAO)", "🚨 Filtros Críticos"])

# --- ABA 1: FROTA (CÓDIGO ANTIGO LEVEMENTE ADAPTADO) ---
with tab1:
    st.markdown("### Aeroportos Monitorados")
    conn = st.connection("supabase", type="sql") # Conexão direta para funções rápidas
    
    # ... (Seu código de adicionar/remover ICAO aqui - pode manter o que você já tinha) ...
    # Vou resumir para focar na parte nova, mas mantenha sua lógica de ICAO aqui.
    
    # Lógica simplificada de exibição para exemplo (mantenha a sua completa):
    df_frota = db_manager.carregar_frota_monitorada()
    st.write(f"Monitorando: {', '.join(df_frota) if df_frota else 'Nenhum'}")
    
    c1, c2 = st.columns(2)
    novo = c1.text_input("Novo ICAO").upper()
    if c2.button("Adicionar"):
        # (Chame sua função de adicionar ICAO aqui)
        pass

# --- ABA 2: FILTROS CRÍTICOS (A NOVIDADE) ---
with tab2:
    st.markdown("### Configuração da Página de Monitoramento Crítico")
    st.info("Selecione abaixo quais Assuntos e Condições devem aparecer na página de alertas.")

    # 1. Carrega o que já está salvo no banco
    df_configs = db_manager.carregar_filtros_configurados()
    
    # Separa em listas
    assuntos_salvos = df_configs[df_configs['tipo'] == 'assunto']['valor'].tolist()
    condicoes_salvas = df_configs[df_configs['tipo'] == 'condicao']['valor'].tolist()

    # 2. Pega todas as opções possíveis do nosso dicionário oficial
    todas_opcoes_assunto = sorted(list(NOTAM_SUBJECT.values()))
    todas_opcoes_condicao = sorted(list(NOTAM_CONDITION.values()))

    with st.form("form_filtros"):
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("📂 Assuntos de Interesse")
            novos_assuntos = st.multiselect(
                "Selecione (ex: Pista, ILS, Vulcão)",
                options=todas_opcoes_assunto,
                default=[x for x in assuntos_salvos if x in todas_opcoes_assunto],
                height=300
            )
            
        with c2:
            st.subheader("🔧 Condições Críticas")
            novas_condicoes = st.multiselect(
                "Selecione (ex: Fechado, Inoperante, Perigo)",
                options=todas_opcoes_condicao,
                default=[x for x in condicoes_salvas if x in todas_opcoes_condicao],
                height=300
            )
            
        st.write("")
        if st.form_submit_button("💾 Salvar Configuração de Filtros", type="primary"):
            ok1 = db_manager.atualizar_filtros_lote('assunto', novos_assuntos)
            ok2 = db_manager.atualizar_filtros_lote('condicao', novas_condicoes)
            
            if ok1 and ok2:
                st.success("Filtros atualizados com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao salvar.")