import streamlit as st
import pandas as pd
import calendar
import uuid
from datetime import datetime, time, timedelta
from utils import db_manager, ui

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
# INICIALIZAÇÃO DE ESTADO
# ==============================================================================
if 'dias_selecionados' not in st.session_state: st.session_state.dias_selecionados = set()
if 'notam_ativo' not in st.session_state: st.session_state.notam_ativo = None
if 'cache_slots' not in st.session_state: st.session_state.cache_slots = [] 
if 'editing_block_id' not in st.session_state: st.session_state.editing_block_id = None 
if 'show_editor' not in st.session_state: st.session_state.show_editor = False

# Garante datas atuais (2026)
if 'ui_ano' not in st.session_state: st.session_state.ui_ano = datetime.now().year
if 'ui_mes_idx' not in st.session_state: st.session_state.ui_mes_idx = datetime.now().month - 1
if 'ui_hora_ini' not in st.session_state: st.session_state.ui_hora_ini = time(8, 0)
if 'ui_hora_fim' not in st.session_state: st.session_state.ui_hora_fim = time(17, 0)

# ==============================================================================
# 1. CARREGAMENTO DE DADOS (COM PROTEÇÃO CONTRA ERROS)
# ==============================================================================
try:
    df_raw = db_manager.carregar_notams()
except Exception:
    df_raw = pd.DataFrame()

if df_raw.empty:
    st.warning("Banco de dados vazio ou erro na conexão.")
    st.stop()

# --- TRATAMENTO ROBUSTO DE DADOS ---
# 1. Cópia limpa e reset de índice (Evita ValueError)
df_notams = df_raw.copy().reset_index(drop=True)

# 2. Renomeia colunas do Supabase para o padrão do App
mapeamento = {'icaoairport_id': 'loc', 'id': 'n'}
df_notams = df_notams.rename(columns=mapeamento)

# 3. Garante que colunas essenciais existam
for col in ['loc', 'n', 'assunto_desc', 'condicao_desc', 'b', 'c', 'd', 'e']:
    if col not in df_notams.columns:
        df_notams[col] = "N/I"
    else:
        df_notams[col] = df_notams[col].fillna("N/I").astype(str)

# 4. Cria ID único usando .apply (Evita erro de índice)
df_notams['id_notam'] = df_notams.apply(lambda x: f"{x['loc']}_{x['n']}", axis=1)

# 5. Filtragem (Mantendo compatibilidade)
df_critico = df_notams.copy()

# ==============================================================================
# FUNÇÕES DE CALLBACK
# ==============================================================================
def limpar_editor_callback():
    st.session_state.dias_selecionados = set()
    st.session_state.editing_block_id = None
    # Reset para data atual
    st.session_state.ui_ano = datetime.now().year 
    st.session_state.ui_mes_idx = datetime.now().month - 1
    st.session_state.ui_hora_ini = time(8, 0)
    st.session_state.ui_hora_fim = time(17, 0)
    st.session_state.show_editor = False

def novo_bloco_callback():
    limpar_editor_callback()
    st.session_state.show_editor = True

def carregar_bloco_callback(block_id):
    slots_do_bloco = [s for s in st.session_state.cache_slots if s['block_id'] == block_id]
    if not slots_do_bloco: return

    st.session_state.dias_selecionados = set()
    first_slot = slots_do_bloco[0]
    
    # Processa datas
    for s in slots_do_bloco:
        val = s['start']
        dt_start = datetime.fromisoformat(val) if isinstance(val, str) else val
        st.session_state.dias_selecionados.add(dt_start.strftime("%Y-%m-%d"))

    dt_ref = datetime.fromisoformat(first_slot['start']) if isinstance(first_slot['start'], str) else first_slot['start']
    dt_end_ref = datetime.fromisoformat(first_slot['end']) if isinstance(first_slot['end'], str) else first_slot['end']
    
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
        st.toast("⚠️ Selecione dias!", icon="⚠️")
        return

    if st.session_state.editing_block_id:
        b_id = st.session_state.editing_block_id
        st.session_state.cache_slots = [s for s in st.session_state.cache_slots if s['block_id'] != b_id]
    else:
        b_id = str(uuid.uuid4())

    novos = []
    h_i, h_f = st.session_state.ui_hora_ini, st.session_state.ui_hora_fim
    delta_d = 1 if h_f < h_i else 0
    
    for s_dt in sorted(st.session_state.dias_selecionados):
        dt_base = datetime.strptime(s_dt, "%Y-%m-%d")
        ini = datetime.combine(dt_base, h_i)
        fim = datetime.combine(dt_base + timedelta(days=delta_d), h_f)
        novos.append({
            "id": str(uuid.uuid4()), "notam_id": st.session_state.notam_ativo,
            "block_id": b_id, "start": ini.isoformat(), "end": fim.isoformat()
        })
    
    st.session_state.cache_slots.extend(novos)
    db_manager.salvar_slots_manuais(st.session_state.notam_ativo, st.session_state.cache_slots)
    st.toast("Salvo!", icon="💾")
    limpar_editor_callback()

def excluir_bloco_callback():
    if st.session_state.editing_block_id:
        b_id = st.session_state.editing_block_id
        st.session_state.cache_slots = [s for s in st.session_state.cache_slots if s['block_id'] != b_id]
        db_manager.salvar_slots_manuais(st.session_state.notam_ativo, st.session_state.cache_slots)
        st.toast("Excluído!", icon="🗑️")
        limpar_editor_callback()

# ==============================================================================
# 2. INTERFACE
# ==============================================================================
tab_cadastro, tab_cronograma = st.tabs(["🛠️ Cadastro", "📅 Visão Geral"])

with tab_cadastro:
    # --- SEÇÃO 1: NOTAMS (LARGURA TOTAL) ---
    st.subheader("1. NOTAMs")
    
    # Prepara dados para tabela
    df_sel = df_critico[['id_notam', 'loc', 'n', 'assunto_desc']].copy().reset_index(drop=True)
    df_sel['Rotulo'] = df_sel.apply(lambda x: f"{x['loc']} {x['n']}", axis=1) # Seguro contra erros
    
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

    # --- SEÇÃO 2: BLOCOS / DADOS / CALENDÁRIO (3 COLUNAS) ---
    col_blocos, col_dados, col_editor = st.columns([1, 1.2, 2.5])

    # COLUNA 1: BLOCOS
    with col_blocos:
        st.subheader("2. Blocos")
        if notam_selecionado is None:
            st.info("👈 Selecione um NOTAM.")
        else:
            st.button("✨ Novo Bloco", use_container_width=True, type="secondary", on_click=novo_bloco_callback)
            if st.session_state.cache_slots:
                st.markdown("---")
                df_slots = pd.DataFrame(st.session_state.cache_slots)
                # Converte para datetime de forma segura
                df_slots['start_dt'] = df_slots['start'].apply(lambda x: datetime.fromisoformat(x) if isinstance(x, str) else x)
                df_slots['end_dt'] = df_slots['end'].apply(lambda x: datetime.fromisoformat(x) if isinstance(x, str) else x)
                
                df_blocos = df_slots.groupby('block_id').agg(
                    inicio_min=('start_dt', 'min'),
                    h_ini=('start_dt', lambda x: x.iloc[0].strftime('%H:%M')),
                    h_fim=('end_dt', lambda x: x.iloc[0].strftime('%H:%M')),
                ).reset_index().sort_values('inicio_min')

                st.caption("Clique para Editar:")
                for _, row in df_blocos.iterrows():
                    b_id = row['block_id']
                    lbl = f"{row['inicio_min'].strftime('%d/%m')} | {row['h_ini']}-{row['h_fim']}"
                    tipo = "primary" if st.session_state.editing_block_id == b_id else "secondary"
                    st.button(lbl, key=f"btn_{b_id}", type=tipo, use_container_width=True, on_click=carregar_bloco_callback, args=(b_id,))

    # COLUNA 2: DADOS DE REFERÊNCIA
    with col_dados:
        st.subheader("📖 Dados")
        if notam_selecionado is not None:
            with st.container(border=True):
                st.caption(f"Vigência: {notam_selecionado['b']} até {notam_selecionado['c']}")
                st.divider()
                st.caption("Texto / Schedule:")
                st.info(f"{notam_selecionado['e']}\n\nSchedule: {notam_selecionado['d']}")

    # COLUNA 3: CALENDÁRIO (Visível apenas se Editor Ativo)
    with col_editor:
        if notam_selecionado is not None and st.session_state.show_editor:
            modo = "EDITANDO" if st.session_state.editing_block_id else "NOVO"
            st.subheader(f"3. Calendário ({modo})")
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.number_input("Ano", 2025, 2030, key="ui_ano")
                nomes_mes = list(calendar.month_name)[1:]
                sel_m = c2.selectbox("Mês", nomes_mes, index=st.session_state.ui_mes_idx)
                st.session_state.ui_mes_idx = nomes_mes.index(sel_m)
                
                c3.time_input("Início UTC", key="ui_hora_ini")
                c4.time_input("Fim UTC", key="ui_hora_fim")

                st.divider()
                # Renderiza Calendário
                ano, mes = st.session_state.ui_ano, st.session_state.ui_mes_idx + 1
                cal = calendar.monthcalendar(ano, mes)
                
                cols = st.columns(7)
                for i, d in enumerate(["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]):
                    cols[i].caption(d)
                
                for semana in cal:
                    cols = st.columns(7)
                    for i, dia in enumerate(semana):
                        if dia != 0:
                            k = f"{ano}-{mes:02d}-{dia:02d}"
                            cor = "primary" if k in st.session_state.dias_selecionados else "secondary"
                            cols[i].button(f"{dia}", key=f"c_{k}", type=cor, use_container_width=True, on_click=toggle_dia_callback, args=(ano, mes, dia))

            c_s, c_d = st.columns([3, 1])
            c_s.button("💾 Salvar", type="primary", use_container_width=True, on_click=salvar_bloco_callback)
            if st.session_state.editing_block_id:
                c_d.button("🗑️", type="secondary", use_container_width=True, on_click=excluir_bloco_callback)

    # --- SEÇÃO 3: ANÁLISE DETALHADA (LARGURA TOTAL) ---
    if notam_selecionado is not None and st.session_state.show_editor:
        st.divider()
        st.subheader("4. Análise Detalhada dos Slots")
        if st.session_state.cache_slots:
            df_a = pd.DataFrame(st.session_state.cache_slots)
            df_a['start'] = df_a['start'].apply(lambda x: datetime.fromisoformat(x) if isinstance(x, str) else x)
            df_a['end'] = df_a['end'].apply(lambda x: datetime.fromisoformat(x) if isinstance(x, str) else x)
            
            df_display = pd.DataFrame({
                "Data": df_a['start'].dt.strftime('%d/%m/%Y'),
                "Dia": df_a['start'].dt.strftime('%A'),
                "Início UTC": df_a['start'].dt.strftime('%H:%M'),
                "Fim UTC": df_a['end'].dt.strftime('%H:%M')
            }).sort_values('Data')
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)

with tab_cronograma:
    st.info("Visão global do cronograma (Em desenvolvimento)")