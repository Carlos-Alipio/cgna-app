import streamlit as st
import pandas as pd

st.title("⚙️ Configurações")

# --- 🔒 BLOCO DE SEGURANÇA (COLE ISSO NO TOPO DAS PÁGINAS) ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.set_page_config(layout="centered") # Força layout pequeno
    st.error("⛔ **Acesso Negado!**")
    st.info("Você precisa fazer login para acessar o sistema de dados.")
    st.stop() # <--- O COMANDO MÁGICO: Para de rodar o código aqui.
# -------------------------------------------------------------

# ... Daqui para baixo fica o seu código normal (st.set_page_config, st.title, etc) ...

