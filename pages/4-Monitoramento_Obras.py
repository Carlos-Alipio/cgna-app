import streamlit as st
import pandas as pd
import calendar
import uuid
from datetime import datetime, time, timedelta
from utils import db_manager, formatters, timeline_processor, pdf_generator

# ==============================================================================
# CONFIGURAÇÃO E ESTILIZAÇÃO
# ==============================================================================
st.set_page_config(page_title="Gestão de Obras", layout="wide")
st.title("🚨 Monitoramento & Cadastro de Obras")

# CSS para alinhar botões à esquerda (parecer lista) e ajustar altura
st.markdown("""
    <style>
    div[data-testid="column"] button {
        text-align: left !important;
    }
    .stButton button {
        min-height: 45px;
    }
    /* Destaque para bloco ativo */
    .bloco-ativo {
        border: 2px solid #7C3AED !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# INICIALIZAÇÃO DE ESTADO (SESSION STATE)
# ==============================================================================
if 'dias_selecionados' not in st.session_state: st.session_state.dias_selecionados = set()
if 'notam_ativo' not in st.session_state: st.session_state.notam_ativo = None
if 'cache_slots' not in st.session_state: st.session_state.cache_slots = [] 
if 'editing_block_id' not in st.session_state: st.session_state.editing_block_id = None 

# Variáveis de UI (Persistência dos Widgets do Editor)
if 'ui_ano' not in st.session_state: st.session_state.ui_ano = datetime.now().year
if 'ui_mes_idx' not in st.session_state: st.session_state.ui_mes_idx = datetime.now().month - 1
if 'ui_hora_ini' not in st.session_state: st.session_state.ui_hora_ini = time(8, 0)
if 'ui_hora_fim' not in st.session_state: st.session_state.ui_hora_fim = time(17, 0)

# ==============================================================================
# 1. CARREGAMENTO DE DADOS (COM LIMPEZA DE ÓRFÃOS)
# ==============================================================================
df_notams = db_manager.carregar_notams()
df_config = db_manager.carregar_filtros_configurados()

if df_notams.empty:
    st.warning("Banco de dados vazio.")
    st.stop()

# Garante ID único para os NOTAMs (Loc + Numero)
if 'id_notam' not in df_notams.columns:
    df_notams['loc'] = df_notams['loc'].astype(str)
    df_notams['n'] = df_notams['n'].astype(str)
    df_notams['id_notam'] = df_notams['loc'] + "_" + df_notams['n']

# Filtros
filtros_assunto = df_config[df_config['tipo'] == 'assunto']['valor'].tolist()
filtros_condicao = df_config[df_config['tipo'] == 'condicao']['valor'].tolist()

# Aplica Filtros (Frota + Críticos)
frota = db_manager.carregar_frota_monitorada()
df_base = df_notams[df_notams['loc'].isin(frota)] if frota else df_notams
mask_assunto = df_base['assunto_desc'].isin(filtros_assunto)
mask_condicao = df_base['condicao_desc'].isin(filtros_condicao)
df_critico = df_base[mask_assunto & mask_condicao].copy()

# Limpeza de dados órfãos (Remove cadastros de NOTAMs que saíram da lista)
ids_ativos = df_critico['id_notam'].unique().tolist()
db_manager.limpar_registros_orfaos(ids_ativos)

# ==============================================================================
# FUNÇÕES DE CALLBACK (LÓGICA DO SISTEMA)
# ==============================================================================

def limpar_editor_callback():
    """Reseta o editor para o estado 'Novo Bloco'"""
    st.session_state.dias_selecionados = set()
    st.session_state.editing_block_id = None
    st.session_state.ui_hora_ini = time(8, 0)
    st.session_state.ui_hora_fim = time(17, 0)

def carregar_bloco_callback(block_id):
    """Carrega um bloco existente para o editor"""
    slots_do_bloco = [s for s in st.session_state.cache_slots if s['block_id'] == block_id]
    
    if not slots_do_bloco: return

    st.session_state.dias_selecionados = set()
    first_slot = None
    
    for s in slots_do_bloco:
        start_val = s['start']
        if isinstance(start_val, str):
            dt_start = datetime.fromisoformat(start_val)
        else:
            dt_start = start_val
            
        st.session_state.dias_selecionados.add(dt_start.strftime("%Y-%m-%d"))
        if first_slot is None: first_slot = s

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

def toggle_dia_callback(a, m, d):
    """Marca/Desmarca um dia no calendário"""
    k = f"{a}-{m:02d}-{d:02d}"
    if k in st.session_state.dias_selecionados:
        st.session_state.dias_selecionados.remove(k)
    else:
        st.session_state.dias_selecionados.add(k)

def salvar_bloco_callback():
    """Salva o bloco no banco e atualiza a interface"""
    if not st.session_state.dias_selecionados:
        st.toast("⚠️ Selecione dias no calendário!", icon="⚠️")
        return

    h_ini = st.session_state.ui_hora_ini
    h_fim = st.session_state.ui_hora_fim
    is_overnight = h_fim < h_ini
    
    if st.session_state.editing_block_id:
        block_id_final = st.session_state.editing_block_id
        st.session_state.cache_slots = [
            s for s in st.session_state.cache_slots 
            if s['block_id'] != block_id_final
        ]
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
    st.toast("✅ Bloco salvo com sucesso!", icon="💾")
    limpar_editor_callback()

def excluir_bloco_callback():
    """Exclui o bloco atual"""
    if st.session_state.editing_block_id:
        b_id = st.session_state.editing_block_id
        st.session_state.cache_slots = [
            s for s in st.session_state.cache_slots 
            if s['block_id'] != b_id
        ]
        db_manager.salvar_slots_manuais(st.session_state.notam_ativo, st.session_state.cache_slots)
        st.toast("🗑️ Bloco excluído!", icon="🗑️")
        limpar_editor_callback()

# ==============================================================================
# 2. INTERFACE DE USUÁRIO (LAYOUT)
# ==============================================================================

tab_cadastro, tab_cronograma = st.tabs(["🛠️ Cadastro & Edição", "📅 Visão Geral"])

with tab_cadastro:
    # --- ÁREA SUPERIOR: EDITOR E BLOCOS ---
    col_notam, col_blocos, col_editor = st.columns([1.2, 1.2, 2.5])

    # COLUNA 1: SELEÇÃO DE NOTAM
    with col_notam:
        st.subheader("1. NOTAMs")
        df_sel = df_critico[['id_notam', 'loc', 'n', 'assunto_desc']].copy()
        df_sel['Rotulo'] = df_sel['loc'] + " " + df_sel['n']
        
        event = st.dataframe(
            df_sel[['Rotulo', 'assunto_desc']],
            column_config={"Rotulo": "Ref", "assunto_desc": "Obra"},
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            height=550
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

    # COLUNA 2: LISTA DE BLOCOS
    with col_blocos:
        st.subheader("2. Blocos")
        
        if notam_selecionado is None:
            st.info("👈 Selecione um NOTAM.")
        else:
            st.button("✨ Novo Bloco", use_container_width=True, type="secondary", on_click=limpar_editor_callback)
            st.markdown("---")
            
            if st.session_state.cache_slots:
                df_slots = pd.DataFrame(st.session_state.cache_slots)
                df_slots['start_dt'] = pd.to_datetime(df_slots['start'])
                df_slots['end_dt'] = pd.to_datetime(df_slots['end'])
                
                df_blocos = df_slots.groupby('block_id').agg(
                    inicio_min=('start_dt', 'min'),
                    inicio_max=('start_dt', 'max'),
                    h_ini=('start_dt', lambda x: x.iloc[0].strftime('%H:%M')),
                    h_fim=('end_dt', lambda x: x.iloc[0].strftime('%H:%M')),
                    qtd=('id', 'count')
                ).reset_index().sort_values('inicio_min')

                st.caption("Clique para Editar:")
                
                for _, row in df_blocos.iterrows():
                    b_id = row['block_id']
                    
                    # Formatação Personalizada (Local - Num - Data - Hora)
                    loc = notam_selecionado['loc']
                    num = notam_selecionado['n']
                    dias = f"{row['inicio_min'].strftime('%d/%m')} a {row['inicio_max'].strftime('%d/%m')}"
                    horas = f"{row['h_ini']} - {row['h_fim']}"
                    lbl = f"{loc}-{num} | {dias} | ⏰ {horas}"
                    
                    tipo_btn = "primary" if st.session_state.editing_block_id == b_id else "secondary"
                    
                    st.button(lbl, key=f"btn_blk_{b_id}", type=tipo_btn, use_container_width=True, on_click=carregar_bloco_callback, args=(b_id,))
            else:
                st.caption("Nenhum bloco cadastrado.")

    # COLUNA 3: EDITOR VISUAL
    with col_editor:
        if notam_selecionado is not None:
            modo = "✏️ EDITANDO BLOCO" if st.session_state.editing_block_id else "➕ NOVO BLOCO"
            st.subheader(f"3. Calendário ({modo})")
            
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                
                c1.number_input("Ano", 2025, 2030, key="ui_ano")
                
                mes_nomes = list(calendar.month_name)[1:]
                sel_mes = c2.selectbox("Mês", mes_nomes, index=st.session_state.ui_mes_idx, key="widget_mes")
                st.session_state.ui_mes_idx = mes_nomes.index(sel_mes)
                mes_idx = st.session_state.ui_mes_idx + 1

                c3.time_input("Início UTC", key="ui_hora_ini")
                c4.time_input("Fim UTC", key="ui_hora_fim")

                if st.session_state.ui_hora_fim < st.session_state.ui_hora_ini:
                    st.warning("🌙 Slot Noturno (Overnight)")

                st.divider()

                ano_atual = st.session_state.ui_ano
                cal_matrix = calendar.monthcalendar(ano_atual, mes_idx)
                cols_h = st.columns(7)
                dias_sem = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
                for i, d in enumerate(dias_sem): cols_h[i].markdown(f"<div style='text-align:center; color: #888; font-size: 0.8rem'>{d}</div>", unsafe_allow_html=True)

                for semana in cal_matrix:
                    cols = st.columns(7)
                    for i, dia in enumerate(semana):
                        if dia != 0:
                            chave = f"{ano_atual}-{mes_idx:02d}-{dia:02d}"
                            is_selected = chave in st.session_state.dias_selecionados
                            b_type = "primary" if is_selected else "secondary"
                            cols[i].button(f"{dia}", key=f"cal_{chave}", type=b_type, use_container_width=True, on_click=toggle_dia_callback, args=(ano_atual, mes_idx, dia))
                        else:
                            cols[i].write("")

            col_save, col_del = st.columns([3, 1])
            with col_save:
                lbl_save = "💾 Atualizar Bloco" if st.session_state.editing_block_id else "✅ Criar Bloco"
                st.button(lbl_save, type="primary", use_container_width=True, on_click=salvar_bloco_callback)

            with col_del:
                if st.session_state.editing_block_id:
                    st.button("🗑️ Excluir", type="secondary", use_container_width=True, on_click=excluir_bloco_callback)

    # --- ÁREA INFERIOR: TABELA DE ANÁLISE (LISTBOX SOLICITADO) ---
    st.divider()
    st.subheader("4. Análise Detalhada dos Slots Cadastrados")
    
    if st.session_state.cache_slots:
        # Prepara tabela de análise
        df_analise = pd.DataFrame(st.session_state.cache_slots)
        df_analise['start_dt'] = pd.to_datetime(df_analise['start'])
        df_analise['end_dt'] = pd.to_datetime(df_analise['end'])
        
        # Cria colunas amigáveis
        df_analise['Data Início'] = df_analise['start_dt'].dt.strftime('%d/%m/%Y')
        df_analise['Hora Início'] = df_analise['start_dt'].dt.strftime('%H:%M')
        df_analise['Data Fim'] = df_analise['end_dt'].dt.strftime('%d/%m/%Y')
        df_analise['Hora Fim'] = df_analise['end_dt'].dt.strftime('%H:%M')
        df_analise['Dia Semana'] = df_analise['start_dt'].dt.strftime('%A').replace('Monday','SEG').replace('Tuesday','TER').replace('Wednesday','QUA').replace('Thursday','QUI').replace('Friday','SEX').replace('Saturday','SÁB').replace('Sunday','DOM')
        
        # Ordena cronologicamente
        df_analise = df_analise.sort_values('start_dt')
        
        # Exibe Dataframe (ListBox)
        st.dataframe(
            df_analise[['Data Início', 'Hora Início', 'Data Fim', 'Hora Fim', 'Dia Semana']],
            use_container_width=True,
            hide_index=True,
            height=300
        )
    else:
        st.info("Nenhum slot cadastrado para análise.")

# --------------------------------------------------------------------------
# ABA 2: VISÃO GERAL (TABELA CONSOLIDADA)
# --------------------------------------------------------------------------
with tab_cronograma:
    if st.session_state.cache_slots:
        st.info("Visão somente leitura dos slots cadastrados.")
        # Reutiliza o dataframe preparado acima
        df_view = pd.DataFrame(st.session_state.cache_slots)
        df_view['start'] = pd.to_datetime(df_view['start'])
        df_view['end'] = pd.to_datetime(df_view['end'])
        df_view = df_view.sort_values('start')
        
        st.dataframe(
            df_view[['start', 'end']],
            column_config={
                "start": st.column_config.DatetimeColumn("Início", format="DD/MM/YYYY HH:mm"),
                "end": st.column_config.DatetimeColumn("Fim", format="DD/MM/YYYY HH:mm")
            },
            use_container_width=True,
            height=600
        )
    else:
        st.warning("Selecione um NOTAM e cadastre horários para visualizar o cronograma.")