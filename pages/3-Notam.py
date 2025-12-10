import streamlit as st
import pandas as pd
import requests
import xmltodict
from sqlalchemy import text # Necessário para comandos SQL manuais
from datetime import datetime # <--- Adicione este import se não tiver

def formatar_data_notam(texto_bruto):
    """
    Recebe: '2511032105' (YYMMDDHHmm)
    Retorna: '03/11/2025 21:05'
    """
    if not isinstance(texto_bruto, str):
        return "-"
    
    texto = texto_bruto.strip() # Remove espaços extras
    
    # Se for "PERM" ou "EST", devolve o texto original sem mexer
    if not texto.isdigit() or len(texto) != 10:
        return texto 

    try:
        # 1. Transforma o texto em um Objeto de Data (entende que 25 é 2025)
        # %y = Ano 2 digitos, %m = Mês, %d = Dia, %H = Hora, %M = Minuto
        data_obj = datetime.strptime(texto, "%y%m%d%H%M")
        
        # 2. Formata para o padrão brasileiro
        return data_obj.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return texto # Se der erro, devolve o original



st.set_page_config(page_title="Extração Supabase", layout="wide")
st.title("✈️ NOTAM AISWEB")

# --- 🔒 BLOCO DE SEGURANÇA (COLE ISSO NO TOPO DAS PÁGINAS) ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.set_page_config(layout="centered") # Força layout pequeno
    st.error("⛔ **Acesso Negado!**")
    st.info("Você precisa fazer login para acessar o sistema de dados.")
    st.stop() # <--- O COMANDO MÁGICO: Para de rodar o código aqui.
# -------------------------------------------------------------

# ... Daqui para baixo fica o seu código normal (st.set_page_config, st.title, etc) ...

# --- CONFIGURAÇÕES ---
# Pegando a senha do cofre de segredos (secrets.toml)
# O nome "supabase" aqui deve ser o mesmo que você colocou nos colchetes [connections.supabase]
conn = st.connection("supabase", type="sql")

API_KEY = "1279934730"
API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"
BASE_URL = "http://aisweb.decea.mil.br/api/"

# --- FUNÇÕES DO BANCO DE DADOS (AGORA COM POSTGRES) ---
def salvar_no_banco(df):
    try:
        with conn.session as s:
            # if_exists='replace' -> CRUCIAL AGORA: 
            # Isso vai destruir a tabela antiga (com poucas colunas)
            # e criar a nova automaticamente com TODAS as colunas do XML.
            df.to_sql('notams', conn.engine, if_exists='replace', index=False, chunksize=1000)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def ler_do_banco():
    # O st.connection tem cache automático (ttl). 
    # ttl=0 garante que sempre pegue o dado fresco.
    try:
        df = conn.query('SELECT * FROM notams', ttl=0)
        return df
    except:
        return pd.DataFrame()

# --- BUSCA NA API (Mesma lógica de antes) ---
# --- FUNÇÃO DE EXTRAÇÃO (VERSÃO SALVA TUDO) ---
def buscar_notams(icao_code):
    headers = {'Content-Type': 'application/xml'}
    params = {'apiKey': API_KEY, 'apiPass': API_PASS, 'area': 'notam', 'icaocode': icao_code}
    
    with st.spinner(f"Baixando TUDO de {icao_code}..."):
        response = requests.get(BASE_URL, params=params)
    
    if response.status_code == 200:
        dados_dict = xmltodict.parse(response.content)
        try:
            # Caminho para achar os itens no XML
            if 'aisweb' in dados_dict and 'notam' in dados_dict['aisweb'] and 'item' in dados_dict['aisweb']['notam']:
                lista_notams = dados_dict['aisweb']['notam']['item']
            else:
                return None

            # Garante que seja lista mesmo se tiver só 1 item
            if isinstance(lista_notams, dict): lista_notams = [lista_notams]
            
            # 1. Cria o DataFrame com TODAS as colunas que vierem
            df = pd.DataFrame(lista_notams)
            
            # 2. TRUQUE DE MESTRE: Converter tudo para String (Texto)
            # O XML tem dados aninhados (dicionários dentro de dicionários).
            # O PostgreSQL não aceita dicionário Python direto.
            # Convertendo pra string, garantimos que nada quebra o salvamento.
            df = df.astype(str)
            
            return df
            
        except Exception as e:
            st.error(f"Erro ao processar dados: {e}")
            return None
    return None

# ... (Todo o código de cima, imports e funções, continua igual) ...

# --- INTERFACE MASTER-DETAIL ---
st.divider()
st.subheader("✈️ Gerenciador de Dados")

# 1. Área de Controle (Busca)
c1, c2 = st.columns([3, 1]) 
with c1:
    aeroporto = st.text_input("Código ICAO", value="")
with c2:
    st.write("") 
    st.write("") 
    if st.button("🔄 Buscar", type="primary", use_container_width=True):
        df_novo = buscar_notams(aeroporto)
        if df_novo is not None and not df_novo.empty:
            salvar_no_banco(df_novo)
            st.success("Atualizado!")
            st.rerun()

# 2. Área Visual (Tabela + Painel Lateral)
df_banco = ler_do_banco()

if not df_banco.empty:
    st.markdown(f"### 📋 Registros ({len(df_banco)})")

    col_tabela, col_detalhes = st.columns([0.65, 0.35], gap="large")

    with col_tabela:
        # --- NOVIDADE: SELETOR DE COLUNAS ---
        # 1. Definimos quais colunas queremos ver de início
        # (Adapte esta lista se quiser outras como padrão)
        colunas_sugeridas = ['loc', 'b', 'c', 'tp', 'n', 'cod']
        
        # Filtramos para garantir que essas colunas realmente existem no banco
        # (Isso evita erro se o XML mudar um dia)
        padrao = [c for c in colunas_sugeridas if c in df_banco.columns]
        
        # 2. O Multiselect
        cols_visiveis = st.multiselect(
            "👁️ Colunas visíveis:",
            options=df_banco.columns,
            default=padrao,
            placeholder="Escolha as colunas..."
        )
        
        # 3. Criamos uma "view" apenas com as colunas escolhidas
        # Se o usuário tirar tudo, mostramos o padrão para não quebrar
        df_exibicao = df_banco[cols_visiveis] if cols_visiveis else df_banco[padrao]
        
        # ------------------------------------

        st.caption("Selecione uma linha para ver detalhes 👉")
        
        evento = st.dataframe(
            df_exibicao,
            use_container_width=True,
            height=600,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True
        )

    with col_detalhes:
        if len(evento.selection.rows) > 0:
            # --- O PULO DO GATO ---
            # 1. Pegamos qual linha visual foi clicada (ex: linha 0, 1, 2...)
            posicao_visual = evento.selection.rows[0]
            
            # 2. Descobrimos qual é o ÍNDICE REAL dessa linha no dataframe exibido
            indice_real = df_exibicao.index[posicao_visual]
            
            # 3. Usamos o .loc (pelo índice) para buscar os dados no BANCO COMPLETO (df_banco)
            # Assim, mesmo que a coluna 'e' (texto) esteja oculta na tabela,
            # conseguimos pegar ela aqui para exibir nos detalhes!
            dados_linha = df_banco.loc[indice_real]
            # ----------------------

            # --- DESENHANDO O PAINEL DE DETALHES ---
            st.caption("📌 Detalhes do NOTAM")
            c_localidade, c_notam = st.columns(2)

            id_notam = dados_linha.get('loc', 'S/N')
            num_notam = dados_linha.get('n', 'S/N')
            
            with c_localidade:
                st.caption("Localidade:")
                st.markdown(f"#### {id_notam}")

            with c_notam:
                st.caption("Notam:")
                st.markdown(f"#### {num_notam}")
            
            st.markdown("---")
            
            raw_inicio = dados_linha.get('b', '')
            raw_fim = dados_linha.get('c', '')
            data_inicio = formatar_data_notam(raw_inicio)
            data_fim = formatar_data_notam(raw_fim)

            st.caption("📅 Vigência")
            c_inicio, c_fim = st.columns(2)
            
            with c_inicio:
                st.caption("Início (B)")
                st.markdown(f"#### {data_inicio}") 

            with c_fim:
                st.caption("Fim (C)")
                if "PERM" in data_fim:
                    st.markdown(f"#### :red[{data_fim}]") 
                else:
                    st.markdown(f"#### {data_fim}")

            st.markdown("---")
            st.caption("**📝 Texto do NOTAM:**")
            
            # Pega o texto 'e' (mesmo que não esteja selecionado no multiselect acima)
            texto_notam = dados_linha.get('e', 'Sem texto')
            
            st.markdown(
                f"""
                <div style='
                    background-color: rgba(128, 128, 128, 0.1);
                    padding: 15px;
                    border-radius: 8px;
                    border: 1px solid rgba(128, 128, 128, 0.2);
                    font-family: "Source Code Pro", monospace;
                    font-size: 14px;
                    white-space: pre-wrap;
                    line-height: 1.5;
                '>{texto_notam.strip()}</div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("---")

            with st.expander("Ver dados brutos (JSON)"):
                st.json(dados_linha.to_dict())
                
        else:
            st.warning("👈 Clique em uma linha na tabela para ver o painel de detalhes aqui.")
            
else:
    st.info("Banco vazio.")