import streamlit as st
import datetime

# --- NOTE QUE REMOVEMOS A FUNÇÃO get_cookie_manager AQUI ---
# Agora o manager deve ser passado por quem chama as funções.

def get_usuario_cookie(cookie_manager):
    """
    Tenta recuperar o email do usuário salvo no cookie.
    Recebe o cookie_manager instanciado no Home.py.
    """
    # Pega todos os cookies usando o manager passado
    try:
        cookies = cookie_manager.get_all()
        if not cookies:
            return None
        return cookies.get("cgna_user_email")
    except:
        return None

def realizar_login_cookie(cookie_manager, email):
    """
    Grava o email no cookie.
    Recebe o cookie_manager e o email.
    
    NOTA: Removemos o 'expires' pois a biblioteca extra_streamlit_components
    não suporta esse argumento na versão Python, gerando TypeError.
    O cookie será de sessão (apaga ao fechar o navegador).
    """
    # O comando .set() desta biblioteca aceita apenas (cookie, value, key)
    cookie_manager.set("cgna_user_email", email)

def realizar_logout(cookie_manager):
    """
    Apaga o cookie e limpa a sessão.
    """
    # Tenta apagar o cookie
    try:
        cookie_manager.delete("cgna_user_email")
    except:
        pass
    
    if 'logado' in st.session_state:
        st.session_state['logado'] = False
    if 'usuario_atual' in st.session_state:
        st.session_state['usuario_atual'] = None
        
    st.rerun()