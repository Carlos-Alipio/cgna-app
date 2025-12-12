import streamlit as st
import extra_streamlit_components as stx
import datetime

def get_cookie_manager():
    """
    Cria ou recupera o gerenciador de cookies.
    Usa o Session State para garantir que o componente seja instanciado
    apenas UMA vez por sessão, evitando o erro DuplicateElementKey.
    """
    key = "main_auth_cookie_manager"

    # 1. Verifica se já existe na sessão
    if key in st.session_state:
        return st.session_state[key]

    # 2. Se não existe, cria e salva na sessão
    cm = stx.CookieManager(key=key)
    st.session_state[key] = cm
    return cm

def get_usuario_cookie():
    """
    Tenta recuperar o email do usuário salvo no cookie.
    Retorna o email (str) ou None.
    """
    # Instancia (ou recupera) o manager
    cookie_manager = get_cookie_manager()
    
    # Pega todos os cookies
    cookies = cookie_manager.get_all()
    
    if not cookies:
        return None
        
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
    
    # Limpa estados do Streamlit
    if 'logado' in st.session_state:
        st.session_state['logado'] = False
    if 'usuario_atual' in st.session_state:
        st.session_state['usuario_atual'] = None
    
    # Remove o manager da sessão para forçar recriação limpa no reload
    if "main_auth_cookie_manager" in st.session_state:
        del st.session_state["main_auth_cookie_manager"]
        
    st.rerun()