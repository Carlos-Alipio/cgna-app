import streamlit as st
import time
import hashlib
import extra_streamlit_components as stx
from utils import login_manager, ui

# Configuração inicial
st.set_page_config(
    page_title="CGNA - GOL", 
    page_icon="assets/logo-voegol-new.svg", 
    layout="wide",
    initial_sidebar_state="expanded" # Garante que o menu inicie aberto
)

cookie_manager = stx.CookieManager(key="main_auth_interface")
conn = st.connection("supabase", type="sql")

def buscar_usuario_por_email(email):
    try:
        df = conn.query(f"SELECT * FROM usuarios WHERE email = '{email}'", ttl=0)
        return df.iloc[0] if not df.empty else None
    except: return None

def criar_hash(senha): return hashlib.sha256(str.encode(senha)).hexdigest()

if 'logado' not in st.session_state: st.session_state['logado'] = False

# Lógica de Login Automático
if not st.session_state['logado']:
    time.sleep(0.1) 
    email_cookie = login_manager.get_usuario_cookie(cookie_manager)
    if email_cookie:
        user_db = buscar_usuario_por_email(email_cookie)
        if user_db is not None: # Correção do ValueError
            st.session_state['logado'] = True
            st.session_state['usuario_atual'] = user_db['nome']
            st.rerun()

# Interface Principal
if not st.session_state['logado']:
    st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
    st.title("🔒 Login CGNA")
    e_log = st.text_input("E-mail")
    s_log = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        u = buscar_usuario_por_email(e_log)
        if u is not None and criar_hash(s_log) == u['senha_hash']:
            st.session_state['logado'] = True
            st.session_state['usuario_atual'] = u['nome']
            login_manager.realizar_login_cookie(cookie_manager, e_log)
            st.rerun()
        else: st.error("Erro nas credenciais.")
else:
    # --- USUÁRIO LOGADO ---
    ui.barra_superior() 
    ui.setup_sidebar()

    pg_home = st.Page("pages/inicio.py", title="Home", icon=":material/home:", default=True)
    pg_notam = st.Page("pages/Notam.py", title="Notam", icon=":material/connecting_airports:")
    pg_obras = st.Page("pages/Monitoramento_Obras.py", title="Gestão de Obras", icon=":material/construction:")
    pg_config = st.Page("pages/Configuracoes.py", title="Configurações", icon=":material/settings:")

    pg = st.navigation({
        "Navegação": [pg_home],
        "Operacional": [pg_notam, pg_obras],
        "Ajustes": [pg_config]
    })

    # Este botão agora será movido para o rodapé automaticamente pelo CSS em ui.py
    if st.sidebar.button("Sair", icon=":material/logout:"):
        login_manager.realizar_logout(cookie_manager)
        st.session_state['logado'] = False
        st.rerun()

    pg.run()