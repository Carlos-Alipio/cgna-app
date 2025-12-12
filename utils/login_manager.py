import streamlit as st
import extra_streamlit_components as stx
import datetime

# Inicializa o gerenciador
@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()

def get_usuario_cookie():
    """
    Tenta recuperar o email do usuário salvo no cookie.
    Retorna o email (str) ou None.
    """
    cookie_manager = get_cookie_manager()
    cookies = cookie_manager.get_all()
    return cookies.get("cgna_user_email")

def realizar_login_cookie(email):
    """
    Grava o email no cookie (validade 7 dias).
    """
    cookie_manager = get_cookie_manager()
    expires = datetime.datetime.now() + datetime.timedelta(days=7)
    
    cookie_manager.set("cgna_user_email", email, expires=expires)

def realizar_logout():
    """
    Apaga o cookie e limpa a sessão.
    """
    cookie_manager = get_cookie_manager()
    cookie_manager.delete("cgna_user_email")
    st.session_state['logado'] = False
    st.session_state['usuario_atual'] = None
    st.rerun()