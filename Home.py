import streamlit as st
import time
import hashlib
from sqlalchemy import text
import extra_streamlit_components as stx # <--- IMPORTANTE
from utils import login_manager

# Configuração da Página
st.set_page_config(
    page_title="CGNA - GOL", 
    page_icon="✈️", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# INICIALIZAÇÃO DO COOKIE MANAGER (UMA VEZ SÓ)
# ==============================================================================
# Criamos o componente aqui no topo para evitar DuplicateKey
cookie_manager = stx.CookieManager(key="main_auth_interface")

# Conexão com Supabase
conn = st.connection("supabase", type="sql")

# --- LISTA VIP ---
EMAILS_PERMITIDOS = [
    "aguedespereira@voegol.com.br",
    "jsgalvao@voegol.com.br",
    "cafmorais@voegol.com.br"
]

# --- FUNÇÕES DE BANCO DE DADOS ---
def buscar_usuario_por_email(email):
    try:
        if not email: return None
        df = conn.query(f"SELECT * FROM usuarios WHERE email = '{email}'", ttl=0)
        if not df.empty:
            return df.iloc[0] 
    except:
        return None
    return None

def salvar_novo_usuario(email, senha_hash, nome):
    if buscar_usuario_por_email(email) is not None:
        return "erro_existe"
    if email not in EMAILS_PERMITIDOS:
        return "erro_permissao"
    try:
        with conn.session as s:
            s.execute(
                text("INSERT INTO usuarios (email, senha_hash, nome) VALUES (:email, :senha, :nome)"),
                params={"email": email, "senha": senha_hash, "nome": nome}
            )
            s.commit()
        return "sucesso"
    except Exception as e:
        st.error(f"Erro no banco: {e}")
        return "erro_banco"

def criar_hash(senha_texto_puro):
    return hashlib.sha256(str.encode(senha_texto_puro)).hexdigest()

def verificar_senha(senha_digitada, hash_armazenado):
    return criar_hash(senha_digitada) == hash_armazenado

# ==============================================================================
# LÓGICA DE SESSÃO
# ==============================================================================

if 'logado' not in st.session_state:
    st.session_state['logado'] = False

# TENTATIVA DE LOGIN AUTOMÁTICO VIA COOKIE
# Passamos o cookie_manager criado no topo
if not st.session_state['logado']:
    # Pequena pausa para garantir que o componente JS carregou
    time.sleep(0.1) 
    email_cookie = login_manager.get_usuario_cookie(cookie_manager)
    
    if email_cookie:
        usuario_db = buscar_usuario_por_email(email_cookie)
        if usuario_db is not None:
            st.session_state['logado'] = True
            st.session_state['usuario_atual'] = usuario_db['nome']
            st.rerun()

# ==============================================================================
# INTERFACE
# ==============================================================================

if not st.session_state['logado']:
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
    
    st.title("🔒 Login CGNA")
    
    tab1, tab2 = st.tabs(["Login", "Criar Conta"])
    
    # --- LOGIN ---
    with tab1:
        email_login = st.text_input("E-mail", key="login_email")
        senha_login = st.text_input("Senha", type="password", key="login_pass")
        
        if st.button("Entrar"):
            usuario = buscar_usuario_por_email(email_login)
            
            if usuario is not None:
                if verificar_senha(senha_login, usuario['senha_hash']):
                    st.session_state['logado'] = True
                    st.session_state['usuario_atual'] = usuario['nome']
                    
                    # GRAVA COOKIE (Passando o manager)
                    login_manager.realizar_login_cookie(cookie_manager, email_login)
                    
                    st.success("Login aprovado! Redirecionando...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
            else:
                st.error("Usuário não encontrado.")

    # --- CADASTRO ---
    with tab2:
        st.write("Cadastro no Banco de Dados Seguro")
        novo_nome = st.text_input("Nome")
        novo_email = st.text_input("E-mail")
        nova_senha = st.text_input("Senha", type="password")
        
        if st.button("Cadastrar"):
            if novo_email and nova_senha:
                hash_senha = criar_hash(nova_senha)
                resultado = salvar_novo_usuario(novo_email, hash_senha, novo_nome)
                
                if resultado == "sucesso":
                    st.success("Cadastrado! Faça login na outra aba.")
                elif resultado == "erro_permissao":
                    st.error("Email não autorizado na lista VIP.")
                elif resultado == "erro_existe":
                    st.error("Usuário já existe.")
            else:
                st.warning("Preencha tudo.")

else:
    st.title(f"Olá, {st.session_state.get('usuario_atual', 'Usuário')}")
    st.success("Você está conectado ao banco de dados Nuvem ☁️")
    st.info("👈 Use o menu lateral para acessar os dados.")
    
    # BOTÃO SAIR (Passando o manager)
    if st.button("Sair"):
        login_manager.realizar_logout(cookie_manager)