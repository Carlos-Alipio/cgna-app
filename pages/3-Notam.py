import streamlit as st
import pandas as pd
import requests
import xmltodict
from sqlalchemy import text
from datetime import datetime
# Importando nosso dicionário de tradução
from notam_codes import NOTAM_SUBJECT, NOTAM_CONDITION

st.set_page_config(page_title="Extração Supabase", layout="wide")
st.title("✈️ NOTAM AISWEB")

# --- 🔒 BLOCO DE SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.set_page_config(layout="centered") 
    st.error("⛔ **Acesso Negado!**")
    st.info("Você precisa fazer login para acessar o sistema de dados.")
    st.stop()
# -----------------------------

# --- CONEXÃO ---
conn = st.connection("supabase", type="sql")

API_KEY = "1279934730"
API_PASS = "cb8a3010-a095-1033-a49b-72567f175e3a"
BASE_URL = "http://aisweb.decea.mil.br/api/"

# --- FUNÇÕES AUXILIARES ---

def formatar_data_notam(texto_bruto):
    """
    Recebe: '2511032105' (YYMMDDHHmm)
    Retorna: '03/11/2025 21:05'
    """
    if not isinstance(texto_bruto, str): return "-"
    texto = texto_bruto.strip()
    if not texto.isdigit() or len(texto) != 10: return texto 
    try:
        data_obj = datetime.strptime(texto, "%y%m%d%H%M")
        return data_obj.strftime("%d/%m/%Y %H:%M")
    except ValueError: return texto

def decodificar_q_code(q_string):
    """
    Traduz o código Q (ex: QMXLC ou MXLC) para texto legível.
    Retorna: (Assunto Texto, Condição Texto, Código Assunto, Código Condição)
    """
    if not isinstance(q_string, str) or len(q_string) < 4:
        return "Outros", "Ver Texto", "XX", "XX"
    
    try:
        # Se começar com Q, pega os caracteres seguintes. Se não, pega do início.
        # Ex: "QMXLC" -> code="MXLC" | "MXLC" -> code="MXLC"
        code = q_string[1:5] if q_string.upper().startswith("Q") else q_string[:4]
        
        ass_cod = code[:2]
        con_cod = code[2:4]
        
        ass_txt = NOTAM_SUBJECT.get(ass_cod, f"Outros ({ass_cod})")
        con_txt = NOTAM_CONDITION.get(con_cod, f"Condição ({con_cod})")
        
        return ass_txt, con_txt, ass_cod, con_cod
    except:
        return "Erro Leitura", "Erro", "XX", "XX"

# --- BANCO DE DADOS ---

def salvar_no_banco(df):
    try:
        with conn.session as s:
            df.to_sql('notams', conn.engine, if_exists='replace', index=False, chunksize=1000)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def ler_do_banco():
    try:
        return conn.query('SELECT * FROM notams', ttl=0)
    except:
        return pd.DataFrame()

# --- BUSCA NA API ---

def buscar_notams(icao_code):
    headers = {'Content-Type': 'application/xml'}
    params = {'apiKey': API_KEY, 'apiPass': API_PASS, 'area': 'notam', 'icaocode': icao_code}
    
    with st.spinner(f"Baixando TUDO de {icao_code}..."):
        response = requests.get(BASE_URL, params=params)
    
    if response.status_code == 200:
        dados_dict = xmltodict.parse(response.content)
        try:
            if 'aisweb' in dados_dict and 'notam' in dados_dict['aisweb'] and 'item' in dados_dict['aisweb']['notam']:
                lista_notams = dados_dict['aisweb']['notam']['item']
            else:
                return None

            if isinstance(lista_notams, dict): lista_notams = [lista_notams]
            
            df = pd.DataFrame(lista_notams)
            
            # --- DETETIVE DE CÓDIGO Q (Procura coluna 'cod' primeiro) ---
            possiveis_nomes = ['cod', 'code', 'q', 'qcode']
            coluna_q = None
            
            for nome in possiveis_nomes:
                if nome in df.columns:
                    coluna_q = nome
                    break
            
            # Se achou a coluna, aplica a decodificação
            if coluna_q:
                df['assunto_desc'], df['condicao_desc'], df['assunto_cod'], df['condicao_cod'] = \
                    zip(*df[coluna_q].apply(decodificar_q_code))
            else:
                df['assunto_desc'] = "N/A"
                df['condicao_desc'] = "N/A"
            # -------------------------------------------------------------
            
            df = df.astype(str)
            return df
            
        except Exception as e:
            st.error(f"Erro ao processar dados: {e}")
            return None
    return None

# --- INTERFACE ---

st.divider()
st.subheader("✈️ Gerenciador de Dados")

# 1. Área de Controle
c1, c2 = st.columns([3, 1]) 
with c1:
    aeroporto = st.text_input("Código ICAO", value="SBGR, SBSP, SBGL, SBRJ, SBBR, SBCF, SBRF, SBSV, SBFZ, SBPA, SBCT, SBFL, SBBE, SBEG, SBGO, SBCY, SBCG, SBSG, SBMO, SBSL, SBTE, SBJP, SBAR, SBPJ, SBPV, SBRB, SBBV, SBMQ, SBFI, SBNF, SBIL, SBPS, SBPL, SBKG, SBCX, SBCH, SBMG, SBLO, SBUL, SBMK, SBJV, SBVT, SBCA, SBSN, SBIZ, SBJU, SBRP, SBIP, SBQV, SAEZ, SABE")
with c2:
    st.write("") 
    st.write("") 
    if st.button("Buscar", type="primary", use_container_width=True):
        if aeroporto:
            df_novo = buscar_notams(aeroporto)
            if df_novo is not None and not df_novo.empty:
                salvar_no_banco(df_novo)
                st.success("Atualizado!")
                st.rerun()
            else:
                st.warning("Nenhum dado encontrado.")
        else:
            st.warning("Digite um ICAO.")

# 2. Área Visual
df_banco = ler_do_banco()

if not df_banco.empty:
    st.markdown(f"### 📋 Registros ({len(df_banco)})")

    col_tabela, col_detalhes = st.columns([0.65, 0.35], gap="large")

    with col_tabela:
        # --- FILTRO POR ASSUNTO (DECODIFICADO) ---
        lista_assuntos = sorted(df_banco['assunto_desc'].unique())
        filtro_assunto = st.multiselect(
            "📂 Filtrar por Assunto:",
            options=lista_assuntos,
            placeholder="Ex: Pista, ILS, Obras..."
        )
        
        if filtro_assunto:
            df_exibicao = df_banco[df_banco['assunto_desc'].isin(filtro_assunto)]
        else:
            df_exibicao = df_banco

        # --- SELETOR DE COLUNAS ---
        # Colunas padrão, incluindo as novas traduzidas
        colunas_sugeridas = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'b', 'c']
        padrao = [c for c in colunas_sugeridas if c in df_exibicao.columns]
        
        cols_visiveis = st.multiselect(
            "👁️ Colunas visíveis:",
            options=df_exibicao.columns,
            default=padrao
        )
        
        df_view = df_exibicao[cols_visiveis] if cols_visiveis else df_exibicao[padrao]
        
        st.caption("Selecione uma linha para ver detalhes 👉")
        
        evento = st.dataframe(
            df_view,
            use_container_width=True,
            height=600,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True
        )

    with col_detalhes:
        if len(evento.selection.rows) > 0:
            # Lógica para pegar a linha certa mesmo com filtros
            posicao_visual = evento.selection.rows[0]
            indice_real = df_exibicao.index[posicao_visual]
            dados_linha = df_banco.loc[indice_real]

            # --- PAINEL DE DETALHES ---
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
            
            st.divider()

            # --- BADGES DECODIFICADOS ---
            subj = dados_linha.get('assunto_desc', 'N/A')
            cond = dados_linha.get('condicao_desc', 'N/A')
            
            st.info(f"Assunto: **{subj}**")
            
            # Cor condicional
            if any(x in cond for x in ['Fechado', 'Inoperante', 'Proibido', 'Retirado']):
                st.error(f"Condição: **{cond}**")
            elif any(x in cond for x in ['Obras', 'Limitado', 'Requer']):
                st.warning(f"Condição: **{cond}**")
            else:
                st.success(f"Condição: **{cond}**")

            st.divider()
            
            # Datas
            raw_inicio = dados_linha.get('b', '')
            raw_fim = dados_linha.get('c', '')
            data_inicio = formatar_data_notam(raw_inicio)
            data_fim = formatar_data_notam(raw_fim)

            st.caption("📅 Vigência")
            c_ini, c_fim = st.columns(2)
            
            with c_ini:
                st.caption("Início (B)")
                st.markdown(f"#### {data_inicio}") 

            with c_fim:
                st.caption("Fim (C)")
                if "PERM" in data_fim:
                    st.markdown(f"#### :red[{data_fim}]") 
                else:
                    st.markdown(f"#### {data_fim}")

            st.divider()
            st.caption("**📝 Texto do NOTAM (Item E):**")
            
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

            st.divider()

            with st.expander("Ver dados brutos (JSON)"):
                st.json(dados_linha.to_dict())
                
        else:
            st.warning("👈 Clique em uma linha na tabela para ver o painel de detalhes aqui.")
            
else:
    st.info("Banco vazio. Busque um aeroporto acima.")