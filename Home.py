import streamlit as st
import time
import hashlib
from sqlalchemy import text
import extra_streamlit_components as stx
from utils import login_manager, ui

# 1. CONFIGURAÇÃO (Sempre o primeiro comando)
st.set_page_config(
    page_title="CGNA - GOL", 
    page_icon="assets/logo-voegol-new.svg", 
    layout="wide"
)

# 2. INICIALIZAÇÃO
cookie_manager = stx.CookieManager(key="main_auth_interface")
conn = st.connection("supabase", type="sql")

def buscar_usuario_por_email(email):
    try:
        # Consulta ao Supabase
        df = conn.query(f"SELECT * FROM usuarios WHERE email = '{email}'", ttl=0)
        # Retorna a primeira linha (Series) se houver resultado, senão None
        return df.iloc[0] if not df.empty else None
    except Exception:
        return None

def criar_hash(senha): 
    return hashlib.sha256(str.encode(senha)).hexdigest()

# Inicializa estado de login
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

# ==============================================================================
# LÓGICA DE AUTO-LOGIN (AQUI ESTAVA O ERRO)
# ==============================================================================
if not st.session_state['logado']:
    # Pequeno delay para carregamento do componente de cookies
    time.sleep(0.1) 
    email_cookie = login_manager.get_usuario_cookie(cookie_manager)
    
    if email_cookie:
        user_db = buscar_usuario_por_email(email_cookie)
        
        # CORREÇÃO: Usamos 'is not None' para evitar o ValueError do Pandas
        if user_db is not None:
            st.session_state['logado'] = True
            st.session_state['usuario_atual'] = user_db['nome']
            st.rerun()

# ==============================================================================
# RENDERIZAÇÃO DA INTERFACE
# ==============================================================================
if not st.session_state['logado']:
    # Tela de Login (Oculta Sidebar)
    st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
    
    st.title("🔒 Login CGNA")
    e_log = st.text_input("E-mail")
    s_log = st.text_input("Senha", type="password")
    
    if st.button("Entrar", use_container_width=True):
        u = buscar_usuario_por_email(e_log)
        # CORREÇÃO: Aqui também usamos 'is not None'
        if u is not None and criar_hash(s_log) == u['senha_hash']:
            st.session_state['logado'] = True
            st.session_state['usuario_atual'] = u['nome']
            login_manager.realizar_login_cookie(cookie_manager, e_log)
            st.rerun()
        else:
            st.error("E-mail ou senha inválidos.")

else:
    # --- USUÁRIO LOGADO ---
    ui.barra_superior() # Injeta a barra azul com Relógio UTC
    ui.setup_sidebar()  # Injeta o logo

    # Definição das Páginas
    pg_home = st.Page("pages/inicio.py", title="Home", icon=":material/home:", default=True)
    pg_obras = st.Page("pages/Monitoramento_Obras.py", title="Gestão de Obras", icon=":material/construction:")
    pg_config = st.Page("pages/Configuracoes.py", title="Ajustes", icon=":material/settings:")

    # Navegação
    pg = st.navigation({
        "Principal": [pg_home],
        "Operacional": [pg_obras, pg_config]
    })

    # Botão Sair na Sidebar
    if st.sidebar.button("Sair", icon=":material/logout:"):
        login_manager.realizar_logout(cookie_manager)
        st.session_state['logado'] = False
        st.rerun()

    pg.run()