import streamlit as st
import pandas as pd

# Importando nossos novos módulos organizados
from utils import db_manager, api_decea, formatters

st.set_page_config(page_title="Monitoramento GOL", layout="wide")
st.title("✈️ Painel de Operações (Modular)")

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

st.divider()

# 1. CONTROLE DE ATUALIZAÇÃO
col_btn, col_info = st.columns([1, 3])
with col_btn:
    if st.button("🔄 Atualizar Base Brasil", type="primary", use_container_width=True):
        # A página não sabe como busca, só pede para a api_decea buscar
        df_novo = api_decea.buscar_firs_brasil()
        
        if df_novo is not None:
            # A página não sabe SQL, só pede para o db_manager salvar
            db_manager.salvar_notams(df_novo)
            st.success(f"Base atualizada! {len(df_novo)} NOTAMs.")
            st.rerun()

# 2. CARREGAR E FILTRAR
df_total = db_manager.carregar_notams()
meus_aeroportos = db_manager.carregar_frota_monitorada()

if not df_total.empty:
    
    # Lógica de visualização
    if meus_aeroportos:
        df_filtrado = df_total[df_total['loc'].isin(meus_aeroportos)]
    else:
        st.warning("⚠️ Lista de monitoramento vazia.")
        df_filtrado = df_total

    with col_info:
        st.metric("NOTAMs da Frota", len(df_filtrado), delta=f"Total Brasil: {len(df_total)}")

    st.divider()

    # Layout Master-Detail
    col_tabela, col_detalhes = st.columns([0.65, 0.35], gap="large")

    with col_tabela:
        assuntos = sorted(df_filtrado['assunto_desc'].unique())
        filtro = st.multiselect("Filtrar Assunto:", assuntos)
        
        df_view = df_filtrado[df_filtrado['assunto_desc'].isin(filtro)] if filtro else df_filtrado
        
        cols_show = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'b', 'c']
        cols_validas = [c for c in cols_show if c in df_view.columns]
        
        evento = st.dataframe(
            df_view[cols_validas],
            use_container_width=True, height=600,
            on_select="rerun", selection_mode="single-row", hide_index=True
        )

    with col_detalhes:
        if len(evento.selection.rows) > 0:
            idx = evento.selection.rows[0]
            dados = df_view.iloc[idx]

            st.info(f"📍 {dados.get('loc')} - NOTAM {dados.get('n')}")
            
            c1, c2 = st.columns(2)
            c1.markdown(f"**Assunto:**\n{dados.get('assunto_desc')}")
            
            cond = dados.get('condicao_desc')
            cor = "red" if any(x in cond for x in ['Fechado','Proibido']) else "green"
            c2.markdown(f"**Condição:**\n:{cor}[{cond}]")
            
            st.divider()
            st.code(dados.get('e', ''), language="text")
            
            c_ini, c_fim = st.columns(2)
            # Usa o formatters.formatar_data_notam
            c_ini.metric("Início", formatters.formatar_data_notam(dados.get('b')))
            c_fim.metric("Fim", formatters.formatar_data_notam(dados.get('c')))

else:
    st.info("Banco vazio.")