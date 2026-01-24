import streamlit as st

# Título de Boas-vindas
st.title("👋 Olá, Carlos Alípio Flores de Morais")

# Status de Conexão (Estilo Alerta Verde)
st.success("Você está conectado.")

# Espaçador visual
st.write("")

# Botão de Sair
if st.button("Sair", icon=":material/logout:"):
    st.info("Lógica de logout aqui...")
