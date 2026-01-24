import streamlit as st

# Pega o nome do Carlos ou de quem estiver logado
nome = st.session_state.get('usuario_atual', 'Usuário')

st.title(f"👋 Olá, {nome}")
st.success("Você está conectado ao sistema.")

st.divider()

# Exemplo de Dashboard simples para a Home
c1, c2, c3 = st.columns(3)
c1.metric("Obras Ativas", "12")
c2.metric("NOTAMs Críticos", "05")
c3.metric("Status do Sistema", "OK")

st.info("Dica: Use o menu lateral para acessar o Monitoramento de Obras.")