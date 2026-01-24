import streamlit as st
import time
import hashlib
from sqlalchemy import text
import extra_streamlit_components as stx

# 1. CONFIGURAÇÃO (OBRIGATORIAMENTE O PRIMEIRO COMANDO)
st.set_page_config(
    page_title="CGNA - GOL", 
    page_icon="assets/logo-voegol-new.svg", 
    layout="wide"
)

# Agora podemos importar seus módulos
from utils import login_manager, ui

# 2. INICIALIZAÇÃO DE COMPONENTES
cookie_manager = stx.CookieManager(key="main_auth_interface")
conn = st.connection("supabase", type="sql")

# --- AUXILIARES ---
EMAILS_PERMITIDOS = ["aguedespereira@voegol.com.br", "jsgalvao@voegol.com.br", "cafmorais@voegol.com.br"]

def buscar_usuario_por_email(email):
    try:
        if not email: return None
        df = conn.query(f"SELECT * FROM usuarios WHERE email = '{email}'", ttl=0)
        return df.iloc[0] if not df.empty else None
    except: return None

def criar_hash(senha): 
    return hashlib.sha256(str.encode(senha)).hexdigest()

# ==============================================================================
# LÓGICA DE SESSÃO E LOGIN
# ==============================================================================
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

# Auto-login via Cookie
if not st.session_state['logado']:
    email_cookie = login_manager.get_usuario_cookie(cookie_manager)
    if email_cookie:
        usuario_db = buscar_usuario_por_email(email_cookie)
        if usuario_db is not None:
            st.session_state['logado'] = True
            st.session_state['usuario_atual'] = usuario_db['nome']
            st.rerun()

# ==============================================================================
# RENDERIZAÇÃO DA INTERFACE
# ==============================================================================
if not st.session_state['logado']:
    # TELA DE LOGIN (SEM SIDEBAR)
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
            else:
                st.error("Credenciais inválidas.")
    with t2:
        st.info("Cadastro habilitado apenas para e-mails autorizados.")

else:
    # USUÁRIO LOGADO: CONFIGURA NAVEGAÇÃO
    ui.setup_sidebar() # Carrega o st.logo
    
    # Definição das Páginas (Caminhos relativos à raiz)
    pg_home = st.Page("pages/inicio.py", title="Home", icon=":material/home:", default=True)
    pg_obras = st.Page("pages/Monitoramento_Obras.py", title="Monitoramento Obras", icon=":material/construction:")
    pg_config = st.Page("pages/Configuracoes.py", title="Configurações", icon=":material/settings:")

    # Navegação com Agrupamento
    pg = st.navigation({
        "Menu": [pg_home],
        "Ferramentas": [pg_obras, pg_config]
    })
    
    # Botão de Sair na Sidebar
    if st.sidebar.button("Sair", icon=":material/logout:"):
        login_manager.realizar_logout(cookie_manager)
        st.session_state['logado'] = False
        st.rerun()

    pg.run()