import streamlit as st
import time
import hashlib
from sqlalchemy import text
import extra_streamlit_components as stx
from utils import login_manager, ui, db_manager

# 1. Configuração da Página (Sempre o primeiro comando)
st.set_page_config(
    page_title="CGNA - GOL", 
    page_icon="assets/logo-voegol-new.svg", 
    layout="centered" if 'logado' not in st.session_state or not st.session_state['logado'] else "wide"
)

# 2. Inicialização de Componentes
cookie_manager = stx.CookieManager(key="main_auth_interface")
conn = st.connection("supabase", type="sql")

# --- LISTA VIP & AUXILIARES ---
EMAILS_PERMITIDOS = ["aguedespereira@voegol.com.br", "jsgalvao@voegol.com.br", "cafmorais@voegol.com.br"]

def buscar_usuario_por_email(email):
    try:
        if not email: return None
        df = conn.query(f"SELECT * FROM usuarios WHERE email = '{email}'", ttl=0)
        return df.iloc[0] if not df.empty else None
    except: return None

def criar_hash(senha): return hashlib.sha256(str.encode(senha)).hexdigest()

# ==============================================================================
# LÓGICA DE AUTENTICAÇÃO
# ==============================================================================
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

# Verificação de Cookie (Auto-login)
if not st.session_state['logado']:
    time.sleep(0.1) 
    email_cookie = login_manager.get_usuario_cookie(cookie_manager)
    if email_cookie:
        usuario_db = buscar_usuario_por_email(email_cookie)
        if usuario_db is not None:
            st.session_state['logado'] = True
            st.session_state['usuario_atual'] = usuario_db['nome']
            st.rerun()

# ==============================================================================
# INTERFACE: LOGIN OU NAVEGAÇÃO
# ==============================================================================
if not st.session_state['logado']:
    # Remove sidebar no login
    st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
    
    st.title("🔒 Login CGNA")
    t1, t2 = st.tabs(["Login", "Criar Conta"])
    
    with t1:
        e_log = st.text_input("E-mail", key="l_email")
        s_log = st.text_input("Senha", type="password", key="l_pass")
        if st.button("Entrar", use_container_width=True):
            user = buscar_usuario_por_email(e_log)
            if user is not None and criar_hash(s_log) == user['senha_hash']:
                st.session_state['logado'] = True
                st.session_state['usuario_atual'] = user['nome']
                login_manager.realizar_login_cookie(cookie_manager, e_log)
                st.rerun()
            else: st.error("Credenciais inválidas.")

    with t2:
        st.info("Entre em contato com o administrador para liberação de e-mails VIP.")
        # Mantenha aqui sua lógica de salvar_novo_usuario se desejar

else:
    # USUÁRIO LOGADO: LIBERA NAVEGAÇÃO
    ui.setup_sidebar() # Exibe o Logo
    
    # Definição das Páginas (Material Symbols!)
    pg_home = st.Page("pages/inicio.py", title="Home", icon=":material/home:", default=True)
    pg_obras = st.Page("pages/Monitoramento_Obras.py", title="Monitoramento Obras", icon=":material/construction:")
    pg_notam = st.Page("pages/Configuracoes.py", title="Configurações", icon=":material/settings:")

    # Botão de Logout Manual na Sidebar
    if st.sidebar.button("Sair", icon=":material/logout:"):
        login_manager.realizar_logout(cookie_manager)
        st.session_state['logado'] = False
        st.rerun()

    # Rodar Navegação
    pg = st.navigation({
        "Menu": [pg_home],
        "Ferramentas": [pg_obras, pg_notam]
    })
    pg.run()