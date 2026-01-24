import streamlit as st

# Recupera o nome do usuário da sessão
nome_usuario = st.session_state.get('usuario_atual', 'Usuário')

st.title(f"Olá, {nome_usuario}")
st.success("Você está conectado ao sistema de Monitoramento CGNA - GOL.")

# Painel de Resumo Visual
st.divider()
c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Obras em Foco", "12")
with c2:
    st.metric("Avisos Recentes", "08")
with c3:
    st.metric("Status API", "Online", delta="Normal")

st.markdown("---")
st.info("Utilize o menu lateral para navegar entre as ferramentas de monitoramento e configuração.")