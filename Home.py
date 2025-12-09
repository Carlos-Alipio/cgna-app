import streamlit as st
import pandas as pd
import os
import time
import hashlib # <--- Biblioteca de segurança

# 1. Configuração Inicial
st.set_page_config(page_title="CGNA - GOL", page_icon="🔒", layout="centered")

ARQUIVO_USUARIOS = 'usuarios.csv'

# --- LISTA VIP (ALLOWLIST) ---
# Em um sistema real, isso poderia vir de outro banco de dados
EMAILS_PERMITIDOS = [
    "admin@empresa.com",
    "gerente@empresa.com",
    "analista@empresa.com",
    "cafmorais@voegol.com.br" # Adicione seu email aqui para testar
]

# 2. Função de Segurança (HASH)
def criar_hash(senha_texto_puro):
    # Transforma "1234" em "03ac674216f3e15c..."
    return hashlib.sha256(str.encode(senha_texto_puro)).hexdigest()

def verificar_senha(senha_digitada, hash_armazenado):
    # Tritura a senha digitada e compara com a triturada guardada
    return criar_hash(senha_digitada) == hash_armazenado

# 3. Funções de Banco de Dados
def carregar_usuarios():
    if not os.path.exists(ARQUIVO_USUARIOS):
        df = pd.DataFrame(columns=['email', 'senha_hash', 'nome'])
        df.to_csv(ARQUIVO_USUARIOS, index=False)
        return df
    return pd.read_csv(ARQUIVO_USUARIOS)

def salvar_usuario(novo_usuario):
    df = carregar_usuarios()
    
    # Verifica se email já está cadastrado
    if novo_usuario['email'] in df['email'].values:
        return "erro_existe"
    
    # --- TRAVA DE SEGURANÇA 1: ALLOWLIST ---
    if novo_usuario['email'] not in EMAILS_PERMITIDOS:
        return "erro_permissao"
    
    # Salva no arquivo
    novo_df = pd.DataFrame([novo_usuario])
    df = pd.concat([df, novo_df], ignore_index=True)
    df.to_csv(ARQUIVO_USUARIOS, index=False)
    return "sucesso"

# 4. Inicializa Sessão
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'usuario_atual' not in st.session_state:
    st.session_state['usuario_atual'] = ''

# 5. Interface
if not st.session_state['logado']:
    st.title("CGNA - GOL")
    
    tab1, tab2 = st.tabs(["Login", "Solicitar Acesso"])
    
    # --- LOGIN ---
    with tab1:
        email_login = st.text_input("E-mail Corporativo", key="login_email")
        senha_login = st.text_input("Senha", type="password", key="login_pass")
        
        if st.button("Acessar"):
            df = carregar_usuarios()
            # Procura o usuário pelo email
            usuario_encontrado = df[df['email'] == email_login]
            
            if not usuario_encontrado.empty:
                # --- TRAVA DE SEGURANÇA 2: VERIFICAR HASH ---
                hash_guardado = usuario_encontrado.iloc[0]['senha_hash']
                if verificar_senha(senha_login, hash_guardado):
                    st.session_state['logado'] = True
                    st.session_state['usuario_atual'] = usuario_encontrado.iloc[0]['nome']
                    st.success("Acesso autorizado.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
            else:
                st.error("E-mail não encontrado no sistema.")

    # --- CADASTRO ---
    with tab2:
        st.write("Ativação de conta para funcionários.")
        novo_nome = st.text_input("Nome Completo")
        novo_email = st.text_input("E-mail (Deve estar na lista autorizada)")
        nova_senha = st.text_input("Crie uma Senha", type="password")
        confirmar = st.text_input("Repita a Senha", type="password")
        
        if st.button("Ativar Conta"):
            if nova_senha != confirmar:
                st.warning("Senhas não conferem.")
            elif not novo_email or not nova_senha:
                st.warning("Preencha tudo.")
            else:
                # CRIA O HASH ANTES DE SALVAR
                senha_protegida = criar_hash(nova_senha)
                
                status = salvar_usuario({
                    'email': novo_email, 
                    'senha_hash': senha_protegida, # <--- Salvamos o hash, não a senha
                    'nome': novo_nome
                })
                
                if status == "sucesso":
                    st.success("Conta ativada! Faça login.")
                elif status == "erro_permissao":
                    st.error("❌ Este e-mail não tem permissão para cadastro. Contate o TI.")
                elif status == "erro_existe":
                    st.error("Este e-mail já possui conta ativa.")

else:
    st.title(f"Olá, {st.session_state['usuario_atual']}")
    st.info("Você está em um ambiente autenticado e seguro.")
    
    if st.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()