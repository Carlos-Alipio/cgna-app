import streamlit as st
import pandas as pd

st.title("⚙️ Configurações")

# --- 🔒 BLOCO DE SEGURANÇA (COLE ISSO NO TOPO DAS PÁGINAS) ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.set_page_config(layout="centered") # Força layout pequeno
    st.error("⛔ **Acesso Negado!**")
    st.info("Você precisa fazer login para acessar o sistema de dados.")
    st.stop() # <--- O COMANDO MÁGICO: Para de rodar o código aqui.
# -------------------------------------------------------------

# ... Daqui para baixo fica o seu código normal (st.set_page_config, st.title, etc) ...

import streamlit as st
import pandas as pd
from sqlalchemy import text

st.set_page_config(page_title="Configurações", layout="centered")
st.title("⚙️ Gerenciar Frota/Destinos")

# --- BLOCO DE SEGURANÇA (Obrigatório) ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

conn = st.connection("supabase", type="sql")

# --- FUNÇÕES ---
def carregar_frota():
    return conn.query("SELECT * FROM frota_icao ORDER BY icao", ttl=0)

def adicionar_icao(icao, desc):
    try:
        with conn.session as s:
            s.execute(
                text("INSERT INTO frota_icao (icao, descricao) VALUES (:i, :d)"),
                params={"i": icao.upper().strip(), "d": desc}
            )
            s.commit()
        return True
    except:
        return False

def remover_icao(icao):
    try:
        with conn.session as s:
            s.execute(
                text("DELETE FROM frota_icao WHERE icao = :i"),
                params={"i": icao}
            )
            s.commit()
        return True
    except:
        return False

# --- INTERFACE ---
tab1, tab2 = st.tabs(["📋 Lista Monitorada", "➕ Adicionar Novos"])

with tab1:
    df = carregar_frota()
    st.write(f"Monitorando **{len(df)}** aeroportos atualmente.")
    
    if not df.empty:
        # Mostra tabela interativa
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Botão para deletar
        col1, col2 = st.columns([3, 1])
        with col1:
            to_delete = st.selectbox("Selecione para remover:", df['icao'])
        with col2:
            st.write("")
            st.write("")
            if st.button("🗑️ Remover"):
                remover_icao(to_delete)
                st.success("Removido!")
                st.rerun()

with tab2:
    st.write("Adicione aeroportos à lista de monitoramento.")
    c1, c2 = st.columns(2)
    novo_icao = c1.text_input("ICAO (ex: SBGR)")
    nova_desc = c2.text_input("Descrição (ex: Hub SP)")
    
    if st.button("Salvar na Lista"):
        if len(novo_icao) == 4:
            if adicionar_icao(novo_icao, nova_desc):
                st.success(f"{novo_icao} adicionado!")
                st.rerun()
            else:
                st.error("Erro: ICAO já existe ou banco indisponível.")
        else:
            st.warning("O código ICAO deve ter 4 letras.")

# --- CARGA EM LOTE (FACILITADOR) ---
with st.expander("🚀 Carga em Lote (Colar Lista)"):
    texto_lote = st.text_area("Cole ICAOs separados por vírgula (Ex: SBGR, SBSP, SBGL)")
    if st.button("Processar Lote"):
        lista = [x.strip().upper() for x in texto_lote.split(',') if len(x.strip()) == 4]
        count = 0
        for i in lista:
            if adicionar_icao(i, "Carga em Lote"):
                count += 1
        st.success(f"{count} aeroportos importados com sucesso!")
        st.rerun()