import streamlit as st

def setup_sidebar():
    # Opção 1 (Fixa)
    #st.logo("assets/logo-voegol-new.svg")
    
    # OU Opção 2 (Grande)
    with st.sidebar:
        st.image("assets/logo.png", width=250)