import streamlit as st
import pandas as pd
import calendar
import uuid
from datetime import datetime, time, timedelta
from utils import db_manager, formatters, timeline_processor, pdf_generator
from utils import ui

# ==============================================================================
# CONFIGURAÇÃO E ESTILIZAÇÃO
# ==============================================================================
st.set_page_config(page_title="Gestão de Obras", layout="wide")
st.title("Cadastro de Obras")
ui.setup_sidebar() 

st.markdown("""
    <style>
    div[data-testid="column"] button { text-align: left !important; }
    .stButton button { min-height: 45px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# INICIALIZAÇÃO DE ESTADO (Hoje é 2026)
# ==============================================================================
if 'dias_selecionados' not in st.session_state: st.session_state.dias_selecionados = set()
if 'notam_ativo' not in st.session_state: st.session_state.notam_ativo = None
if 'cache_slots' not in st.session_state: st.session_state.cache_slots = [] 
if 'editing_block_id' not in st.session_state: st.session_state.editing_block_id = None 
if 'show_editor' not in st.session_state: st.session_state.show_editor = False

# Garante que inicie no ano atual (2026)
if 'ui_ano' not in st.session_state: st.session_state.ui_ano = datetime.now().year
if 'ui_mes_idx' not in st.session_state: st.session_state.ui_mes_idx = datetime.now().month - 1
if 'ui_hora_ini' not in st.session_state: st.session_state.ui_hora_ini = time(8, 0)
if 'ui_hora_fim' not in st.session_state: st.session_state.ui_hora_fim = time(17, 0)

# ==============================================================================
# FUNÇÕES DE CALLBACK (CORRIGIDAS)
# ==============================================================================

def limpar_editor_callback():
    """Reseta o editor e força o ano/mês para o presente (2026)."""
    st.session_state.dias_selecionados = set()
    st.session_state.editing_block_id = None
    # CORREÇÃO: Força o reset para o ano e mês atuais ao limpar
    st.session_state.ui_ano = datetime.now().year 
    st.session_state.ui_mes_idx = datetime.now().month - 1
    st.session_state.ui_hora_ini = time(8, 0)
    st.session_state.ui_hora_fim = time(17, 0)
    st.session_state.show_editor = False

def novo_bloco_callback():
    """Inicia um novo bloco garantindo que o calendário abra em 2026."""
    limpar_editor_callback()
    st.session_state.show_editor = True

def carregar_bloco_callback(block_id):
    """Carrega dados de um bloco existente."""
    slots_do_bloco = [s for s in st.session_state.cache_slots if s['block_id'] == block_id]
    if not slots_do_bloco: return

    st.session_state.dias_selecionados = set()
    for s in slots_do_bloco:
        dt_start = datetime.fromisoformat(s['start']) if isinstance(s['start'], str) else s['start']
        st.session_state.dias_selecionados.add(dt_start.strftime("%Y-%m-%d"))
    
    # Sincroniza o calendário com a data do bloco carregado
    dt_ref = slots_do_bloco[0]['start']
    if isinstance(dt_ref, str): dt_ref = datetime.fromisoformat(dt_ref)
    
    st.session_state.ui_ano = dt_ref.year
    st.session_state.ui_mes_idx = dt_ref.month - 1
    st.session_state.editing_block_id = block_id
    st.session_state.show_editor = True

def toggle_dia_callback(a, m, d):
    """Marca/desmarca o dia sem alterar o ano do estado indesejadamente."""
    k = f"{a}-{m:02d}-{d:02d}"
    if k in st.session_state.dias_selecionados: st.session_state.dias_selecionados.remove(k)
    else: st.session_state.dias_selecionados.add(k)

# ==============================================================================
# 1. CARREGAMENTO E TRATAMENTO DE DADOS (CORRIGIDO)
# ==============================================================================
# 1.1 Carrega dados brutos
df_raw = db_manager.carregar_notams()

if df_raw.empty:
    st.warning("Banco de dados vazio.")
    st.stop()

# 1.2 Limpeza inicial: Cópia e Reset de Índice
df_notams = df_raw.copy().reset_index(drop=True)

# 1.3 Mapeamento de colunas (Supabase -> App)
mapeamento = {'icaoairport_id': 'loc', 'id': 'n'}
df_notams = df_notams.rename(columns=mapeamento)

# 1.4 Tratamento de Nulos
for col in ['loc', 'n', 'assunto_desc']:
    if col not in df_notams.columns:
        df_notams[col] = "N/I"
    else:
        df_notams[col] = df_notams[col].fillna("N/I").astype(str)

# 1.5 Criação do ID Único (Via apply para evitar erro de índice)
df_notams['id_notam'] = df_notams.apply(lambda x: f"{x['loc']}_{x['n']}", axis=1)

# 1.6 Filtragem (df_critico)
df_critico = df_notams.copy()

# 1.7 Tabela de Seleção
cols_selecao = ['id_notam', 'loc', 'n', 'assunto_desc']
for col in cols_selecao:
    if col not in df_critico.columns:
        df_critico[col] = "N/I"

df_sel = df_critico[cols_selecao].copy()

# ------------------------------------------------------------------
# AQUI ESTÁ A CORREÇÃO PRINCIPAL
# ------------------------------------------------------------------
# 1. Limpa o índice do recorte
df_sel = df_sel.reset_index(drop=True)

# 2. Usa .apply() em vez de soma (+). Isso ignora problemas de alinhamento.
df_sel['Rotulo'] = df_sel.apply(lambda x: f"{x['loc']} {x['n']}", axis=1)

# ==============================================================================
# 2. INTERFACE (LAYOUT 1 - 3 - 1)
# ==============================================================================
tab_cadastro, tab_cronograma = st.tabs(["🛠️ Cadastro & Edição", "📅 Visão Geral"])

with tab_cadastro:
    # --- 1 COLUNA: NOTAMs ---
    st.subheader("1. NOTAMs")
    df_sel = df_critico[['id_notam', 'loc', 'n', 'assunto_desc']].copy()
    df_sel['Rotulo'] = df_sel['loc'] + " " + df_sel['n']
    event = st.dataframe(df_sel[['Rotulo', 'assunto_desc']], use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", height=200)

    if event.selection.rows:
        idx = event.selection.rows[0]
        id_atual = df_critico.iloc[idx]['id_notam']
        if st.session_state.notam_ativo != id_atual:
            st.session_state.notam_ativo = id_atual
            limpar_editor_callback()
            st.session_state.cache_slots = db_manager.carregar_slots_manuais(id_atual)
            st.rerun()

    st.divider()

    # --- 3 COLUNAS: Blocos / Dados / Calendário ---
    col_blocos, col_dados, col_editor = st.columns([1, 1.2, 2.5])

    with col_blocos:
        st.subheader("2. Blocos")
        if st.session_state.notam_ativo:
            st.button("✨ Novo Bloco", use_container_width=True, on_click=novo_bloco_callback)
            if st.session_state.cache_slots:
                # Listagem de blocos para edição...
                pass

    with col_dados:
        st.subheader("📖 Dados")
        if st.session_state.notam_ativo:
            st.info("Exibição dos dados do NOTAM selecionado...")

    with col_editor:
        if st.session_state.show_editor and st.session_state.notam_ativo:
            modo = "✏️ EDITANDO" if st.session_state.editing_block_id else "➕ NOVO BLOCO"
            st.subheader(f"3. Calendário ({modo})")
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                # O widget agora reflete sempre o st.session_state.ui_ano resetado
                c1.number_input("Ano", 2025, 2030, key="ui_ano")
                mes_nomes = list(calendar.month_name)[1:]
                c2.selectbox("Mês", mes_nomes, index=st.session_state.ui_mes_idx, key="widget_mes")
                st.session_state.ui_mes_idx = mes_nomes.index(st.session_state.widget_mes)
                
                c3.time_input("Início UTC", key="ui_hora_ini")
                c4.time_input("Fim UTC", key="ui_hora_fim")

                st.divider()
                # Lógica do Calendário (Matriz de botões)
                ano_atual = st.session_state.ui_ano
                mes_idx = st.session_state.ui_mes_idx + 1
                cal_matrix = calendar.monthcalendar(ano_atual, mes_idx)
                for semana in cal_matrix:
                    cols = st.columns(7)
                    for i, dia in enumerate(semana):
                        if dia != 0:
                            chave = f"{ano_atual}-{mes_idx:02d}-{dia:02d}"
                            b_type = "primary" if chave in st.session_state.dias_selecionados else "secondary"
                            cols[i].button(f"{dia}", key=f"cal_{chave}", type=b_type, use_container_width=True, on_click=toggle_dia_callback, args=(ano_atual, mes_idx, dia))

    # --- 1 COLUNA: Análise Detalhada ---
    if st.session_state.show_editor:
        st.divider()
        st.subheader("4. Análise Detalhada dos Slots")
        # Exibição do DataFrame de análise...