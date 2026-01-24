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
    div[data-testid="column"] button {
        text-align: left !important;
    }
    .stButton button {
        min-height: 45px;
    }
    .bloco-ativo {
        border: 2px solid #7C3AED !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# INICIALIZAÇÃO DE ESTADO
# ==============================================================================
if 'dias_selecionados' not in st.session_state: st.session_state.dias_selecionados = set()
if 'notam_ativo' not in st.session_state: st.session_state.notam_ativo = None
if 'cache_slots' not in st.session_state: st.session_state.cache_slots = [] 
if 'editing_block_id' not in st.session_state: st.session_state.editing_block_id = None 

# Trava visual: Controla se o Calendário e a Análise aparecem
if 'show_editor' not in st.session_state: st.session_state.show_editor = False

# Garante que as variáveis de tempo existam (iniciando com o ano atual)
if 'ui_ano' not in st.session_state: st.session_state.ui_ano = datetime.now().year
if 'ui_mes_idx' not in st.session_state: st.session_state.ui_mes_idx = datetime.now().month - 1
if 'ui_hora_ini' not in st.session_state: st.session_state.ui_hora_ini = time(8, 0)
if 'ui_hora_fim' not in st.session_state: st.session_state.ui_hora_fim = time(17, 0)

# ==============================================================================
# 1. CARREGAMENTO DE DADOS
# ==============================================================================
df_notams = db_manager.carregar_notams()
df_config = db_manager.carregar_filtros_configurados()

if df_notams.empty:
    st.warning("Banco de dados vazio.")
    st.stop()

# Ajuste seguro para evitar erros de criação de coluna se elas não existirem
if 'id_notam' not in df_notams.columns:
    df_notams['loc'] = df_notams['loc'].astype(str)
    df_notams['n'] = df_notams['n'].astype(str)
    df_notams['id_notam'] = df_notams['loc'] + "_" + df_notams['n']

filtros_assunto = df_config[df_config['tipo'] == 'assunto']['valor'].tolist()
filtros_condicao = df_config[df_config['tipo'] == 'condicao']['valor'].tolist()

frota = db_manager.carregar_frota_monitorada()
df_base = df_notams[df_notams['loc'].isin(frota)] if frota else df_notams
mask_assunto = df_base['assunto_desc'].isin(filtros_assunto)
mask_condicao = df_base['condicao_desc'].isin(filtros_condicao)
df_critico = df_base[mask_assunto & mask_condicao].copy()

ids_ativos = df_critico['id_notam'].unique().tolist()
db_manager.limpar_registros_orfaos(ids_ativos)

# ==============================================================================
# FUNÇÕES DE CALLBACK
# ==============================================================================

def limpar_editor_callback():
    st.session_state.dias_selecionados = set()
    st.session_state.editing_block_id = None
    
    # --- CORREÇÃO AQUI: FORÇA O ANO E MÊS ATUAIS ---
    # Sempre que limpar o editor (novo bloco ou após salvar), volta para hoje (2026)
    agora = datetime.now()
    st.session_state.ui_ano = agora.year
    st.session_state.ui_mes_idx = agora.month - 1
    # -----------------------------------------------

    st.session_state.ui_hora_ini = time(8, 0)
    st.session_state.ui_hora_fim = time(17, 0)
    st.session_state.show_editor = False 

def novo_bloco_callback():
    limpar_editor_callback()
    st.session_state.show_editor = True # Abre o calendário

def carregar_bloco_callback(block_id):
    slots_do_bloco = [s for s in st.session_state.cache_slots if s['block_id'] == block_id]
    if not slots_do_bloco: return

    st.session_state.dias_selecionados = set()
    first_slot = None
    for s in slots_do_bloco:
        start_val = s['start']
        if isinstance(start_val, str): dt_start = datetime.fromisoformat(start_val)
        else: dt_start = start_val
        st.session_state.dias_selecionados.add(dt_start.strftime("%Y-%m-%d"))
        if first_slot is None: first_slot = s

    # Ao editar, carregamos a data DO BLOCO (pode ser diferente da atual)
    if isinstance(first_slot['start'], str):
        dt_ref = datetime.fromisoformat(first_slot['start'])
        dt_end_ref = datetime.fromisoformat(first_slot['end'])
    else:
        dt_ref = first_slot['start']
        dt_end_ref = first_slot['end']
    
    st.session_state.ui_ano = dt_ref.year
    st.session_state.ui_mes_idx = dt_ref.month - 1
    st.session_state.ui_hora_ini = dt_ref.time()
    st.session_state.ui_hora_fim = dt_end_ref.time()
    st.session_state.editing_block_id = block_id
    st.session_state.show_editor = True 

def toggle_dia_callback(a, m, d):
    k = f"{a}-{m:02d}-{d:02d}"
    if k in st.session_state.dias_selecionados: st.session_state.dias_selecionados.remove(k)
    else: st.session_state.dias_selecionados.add(k)

def salvar_bloco_callback():
    if not st.session_state.dias_selecionados:
        st.toast("⚠️ Selecione dias no calendário!", icon="⚠️")
        return

    h_ini = st.session_state.ui_hora_ini
    h_fim = st.session_state.ui_hora_fim
    is_overnight = h_fim < h_ini
    
    if st.session_state.editing_block_id:
        block_id_final = st.session_state.editing_block_id
        st.session_state.cache_slots = [s for s in st.session_state.cache_slots if s['block_id'] != block_id_final]
    else:
        block_id_final = str(uuid.uuid4())

    novos_slots = []
    for str_dt in sorted(st.session_state.dias_selecionados):
        dt_base = datetime.strptime(str_dt, "%Y-%m-%d")
        ini = datetime.combine(dt_base, h_ini)
        fim = datetime.combine(dt_base + timedelta(days=1 if is_overnight else 0), h_fim)
        
        novos_slots.append({
            "id": str(uuid.uuid4()),
            "notam_id": st.session_state.notam_ativo,
            "block_id": block_id_final,
            "start": ini.isoformat(),
            "end": fim.isoformat()
        })
    
    st.session_state.cache_slots.extend(novos_slots)
    db_manager.salvar_slots_manuais(st.session_state.notam_ativo, st.session_state.cache_slots)
    st.toast("✅ Bloco salvo!", icon="💾")
    limpar_editor_callback()

def excluir_bloco_callback():
    if st.session_state.editing_block_id:
        b_id = st.session_state.editing_block_id
        st.session_state.cache_slots = [s for s in st.session_state.cache_slots if s['block_id'] != b_id]
        db_manager.salvar_slots_manuais(st.session_state.notam_ativo, st.session_state.cache_slots)
        st.toast("🗑️ Bloco excluído!", icon="🗑️")
        limpar_editor_callback()

# ==============================================================================
# 2. INTERFACE
# ==============================================================================

tab_cadastro, tab_cronograma = st.tabs(["🛠️ Cadastro & Edição", "📅 Visão Geral"])

with tab_cadastro:
    
    # --- 1. NOTAMs (Largura Total) ---
    st.subheader("1. NOTAMs")
    
    # Pequena proteção para evitar erros de índice se houver filtragem
    df_sel = df_critico[['id_notam', 'loc', 'n', 'assunto_desc']].copy().reset_index(drop=True)
    df_sel['Rotulo'] = df_sel['loc'] + " " + df_sel['n']
    
    event = st.dataframe(
        df_sel[['Rotulo', 'assunto_desc']],
        column_config={"Rotulo": "Ref", "assunto_desc": "Obra"},
        use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", height=250
    )

    notam_selecionado = None
    if event.selection.rows:
        idx = event.selection.rows[0]
        notam_selecionado = df_critico.iloc[idx]
        id_atual = notam_selecionado['id_notam']

        if st.session_state.notam_ativo != id_atual:
            st.session_state.notam_ativo = id_atual
            limpar_editor_callback()
            st.session_state.cache_slots = db_manager.carregar_slots_manuais(id_atual)
            st.rerun()

    st.divider()

    # --- 3 COLUNAS ---
    col_blocos, col_dados, col_editor = st.columns([1.2, 1.2, 2.5])

    # --- 2. Blocos ---
    with col_blocos:
        st.subheader("2. Blocos")
        if notam_selecionado is None:
            st.info("👈 Selecione um NOTAM.")
        else:
            st.button("✨ Novo Bloco", use_container_width=True, type="secondary", on_click=novo_bloco_callback)
            st.markdown("---")
            if st.session_state.cache_slots:
                df_slots = pd.DataFrame(st.session_state.cache_slots)
                df_slots['start_dt'] = pd.to_datetime(df_slots['start'])
                df_slots['end_dt'] = pd.to_datetime(df_slots['end'])
                
                df_blocos = df_slots.groupby('block_id').agg