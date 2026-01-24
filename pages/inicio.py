import streamlit as st


st.title(f"Olá, {st.session_state.get('usuario_atual', 'Usuário')}")
st.success("Você está conectado ao Monitoramento CGNA.")
st.divider()
