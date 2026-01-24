import streamlit as st
from utils import ui

# Garante que a barra apareça mesmo na troca de página
ui.barra_superior()

nome = st.session_state.get('usuario_atual', 'Usuário')

st.title(f"Bem-vindo, {nome}")
st.success("Acesso autorizado ao painel operacional.")

st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Obras em Monitoramento", "14")
with col2:
    st.metric("NOTAMs Ativos", "22", delta="-3")
with col3:
    st.metric("Tempo Médio de Cadastro", "4m", delta="15s", delta_color="inverse")

st.info("Utilize o menu à esquerda para gerenciar os agendamentos das obras.")
