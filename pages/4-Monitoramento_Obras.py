import streamlit as st
import pandas as pd
import calendar
import uuid
from datetime import datetime, time, timedelta
from utils import db_manager, formatters, timeline_processor, pdf_generator

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gestão de Obras", layout="wide")
st.title("🚨 Monitoramento & Cadastro de Obras")

# --- ESTILIZAÇÃO CUSTOMIZADA (BOTÕES ROXOS E LISTA) ---
st.markdown("""
    <style>
    /* Estilo para a lista de blocos */
    div.stButton > button:first-child {
        text-align: left;
        padding-left: 15px;
    }
    /* Destaque para bloco ativo */
    .bloco-ativo {
        border: 2px solid #7C3AED !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- ESTADOS DE SESSÃO ---
if 'dias_selecionados' not in st.session_state: st.session_state.dias_selecionados = set()
if 'notam_ativo' not in st.session_state: st.session_state.notam_ativo = None
if 'cache_slots' not in st.session_state: st.session_state.cache_slots = [] 
if 'editing_block_id' not in st.session_state: st.session_state.editing_block_id = None # Controla quem estou editando

# --- VARIÁVEIS DE CONTROLE UI (Para forçar atualização dos widgets) ---
if 'ui_ano' not in st.session_state: st.session_state.ui_ano = datetime.now().year
if 'ui_mes_idx' not in st.session_state: st.session_state.ui_mes_idx = datetime.now().month - 1
if 'ui_hora_ini' not in st.session_state: st.session_state.ui_hora_ini = time(8, 0)
if 'ui_hora_fim' not in st.session_state: st.session_state.ui_hora_fim = time(17, 0)

# ==============================================================================
# 1. CARREGAMENTO E PREPARAÇÃO
# ==============================================================================
df_notams = db_manager.carregar_notams()
df_config = db_manager.carregar_filtros_configurados()

if df_notams.empty:
    st.warning("Banco de dados vazio.")
    st.stop()

# Garante ID único
if 'id_notam' not in df_notams.columns:
    df_notams['loc'] = df_notams['loc'].astype(str)
    df_notams['n'] = df_notams['n'].astype(str)
    df_notams['id_notam'] = df_notams['loc'] + "_" + df_notams['n']

# Filtros
filtros_assunto = df_config[df_config['tipo'] == 'assunto']['valor'].tolist()
filtros_condicao = df_config[df_config['tipo'] == 'condicao']['valor'].tolist()

frota = db_manager.carregar_frota_monitorada()
df_base = df_notams[df_notams['loc'].isin(frota)] if frota else df_notams

mask_assunto = df_base['assunto_desc'].isin(filtros_assunto)
mask_condicao = df_base['condicao_desc'].isin(filtros_condicao)
df_critico = df_base[mask_assunto & mask_condicao].copy()

# Limpeza
ids_ativos = df_critico['id_notam'].unique().tolist()
db_manager.limpar_registros_orfaos(ids_ativos)

# ==============================================================================
# FUNÇÕES DE LÓGICA DE INTERFACE
# ==============================================================================

def carregar_bloco_para_edicao(block_id):
    """Recupera dados do bloco e popula o calendário e inputs"""
    slots_do_bloco = [s for s in st.session_state.cache_slots if s['block_id'] == block_id]
    
    if not slots_do_bloco: return

    # 1. Recupera Dias
    st.session_state.dias_selecionados = set()
    first_slot = None
    
    for s in slots_do_bloco:
        # Converte string ISO para datetime se necessário
        dt_start = datetime.fromisoformat(s['start']) if isinstance(s['start'], str) else s['start']
        st.session_state.dias_selecionados.add(dt_start.strftime("%Y-%m-%d"))
        
        if first_slot is None: first_slot = s

    # 2. Recupera Horários e Mês de Referência (baseado no 1º slot)
    dt_ref = datetime.fromisoformat(first_slot['start']) if isinstance(first_slot['start'], str) else first_slot['start']
    dt_end_ref = datetime.fromisoformat(first_slot['end']) if isinstance(first_slot['end'], str) else first_slot['end']
    
    # Atualiza variaveis de UI
    st.session_state.ui_ano = dt_ref.year
    st.session_state.ui_mes_idx = dt_ref.month - 1
    st.session_state.ui_hora_ini = dt_ref.time()
    # Se for overnight, a hora fim é a hora do dia seguinte, mas o objeto time é o mesmo
    st.session_state.ui_hora_fim = dt_end_ref.time()
    
    # 3. Define modo de edição
    st.session_state.editing_block_id = block_id

def limpar_editor():
    """Reseta o calendário para modo 'Novo Bloco'"""
    st.session_state.dias_selecionados = set()
    st.session_state.editing_block_id = None
    # Mantém o mês/ano atual ou reseta, como preferir
    st.session_state.ui_hora_ini = time(8, 0)
    st.session_state.ui_hora_fim = time(17, 0)

def toggle_dia(a, m, d):
    k = f"{a}-{m:02d}-{d:02d}"
    if k in st.session_state.dias_selecionados: st.session_state.dias_selecionados.remove(k)
    else: st.session_state.dias_selecionados.add(k)

# ==============================================================================
# 2. INTERFACE PRINCIPAL
# ==============================================================================

tab_cadastro, tab_cronograma = st.tabs(["🛠️ Cadastro & Edição", "📅 Visão Geral"])

with tab_cadastro:
    # Layout de 3 Colunas: Lista NOTAM | Lista Blocos | Editor Calendário
    col_notam, col_blocos, col_editor = st.columns([1.2, 1.2, 2.5])

    # ----------------------------------------------------------------------
    # COLUNA 1: SELEÇÃO DE NOTAM (Mestre)
    # ----------------------------------------------------------------------
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
                limpar_editor()
                st.session_state.cache_slots = db_manager.carregar_slots_manuais(id_atual)
                st.rerun()

    # ----------------------------------------------------------------------
    # COLUNA 2: LISTA DE BLOCOS (O Listbox Editável)
    # ----------------------------------------------------------------------
    with col_blocos:
        st.subheader("2. Blocos")
        
        if notam_selecionado is None:
            st.info("👈 Selecione um NOTAM.")
        else:
            # Botão Novo Bloco (Limpar)
            if st.button("✨ Novo Bloco", use_container_width=True, type="secondary"):
                limpar_editor()
                st.rerun()
            
            st.markdown("---")
            
            if st.session_state.cache_slots:
                # Agrupa slots por Block ID para criar os botões
                df_slots = pd.DataFrame(st.session_state.cache_slots)
                # Converte para datetime para garantir ordenação e formatação
                df_slots['start'] = pd.to_datetime(df_slots['start'])
                df_slots['end'] = pd.to_datetime(df_slots['end'])
                
                # Agrupamento
                df_blocos = df_slots.groupby('block_id').agg(
                    inicio_min=('start', 'min'),
                    inicio_max=('start', 'max'),
                    horario_str=('start', lambda x: x.iloc[0].strftime('%H:%M')),
                    qtd=('id', 'count')
                ).reset_index().sort_values('inicio_min')

                st.caption("Clique para Editar:")
                
                # Renderiza os botões dos blocos
                for _, row in df_blocos.iterrows():
                    b_id = row['block_id']
                    
                    # Formata label: "05/01 a 12/01 | 08:00 (3d)"
                    lbl_data = f"{row['inicio_min'].strftime('%d/%m')} a {row['inicio_max'].strftime('%d/%m')}"
                    lbl_full = f"{lbl_data} | ⏰ {row['horario_str']} ({row['qtd']}d)"
                    
                    # Se este é o bloco em edição, destaca (Primary), senão (Secondary)
                    tipo_btn = "primary" if st.session_state.editing_block_id == b_id else "secondary"
                    
                    if st.button(lbl_full, key=f"btn_blk_{b_id}", type=tipo_btn, use_container_width=True):
                        carregar_bloco_para_edicao(b_id)
                        st.rerun()
            else:
                st.caption("Nenhum bloco cadastrado.")

    # ----------------------------------------------------------------------
    # COLUNA 3: EDITOR VISUAL (Calendário)
    # ----------------------------------------------------------------------
    with col_editor:
        if notam_selecionado:
            # Título Contextual
            modo = "✏️ EDITANDO BLOCO" if st.session_state.editing_block_id else "➕ NOVO BLOCO"
            st.subheader(f"3. Calendário ({modo})")
            
            with st.container(border=True):
                # A. Inputs de Controle
                c1, c2, c3, c4 = st.columns(4)
                
                # Usa os session_state.ui_... para manter valores ao clicar nos blocos
                ano_sel = c1.number_input("Ano", 2025, 2030, key="ui_ano")
                
                mes_nomes = list(calendar.month_name)[1:]
                mes_sel_txt = c2.selectbox(
                    "Mês", 
                    mes_nomes, 
                    index=st.session_state.ui_mes_idx,
                    key="widget_mes" # Chave diferente para não conflitar diretamente, controlamos via index
                )
                # Atualiza o index no state para sincronia
                st.session_state.ui_mes_idx = mes_nomes.index(mes_sel_txt)
                mes_idx = st.session_state.ui_mes_idx + 1

                hora_ini = c3.time_input("Início UTC", key="ui_hora_ini")
                hora_fim = c4.time_input("Fim UTC", key="ui_hora_fim")

                if hora_fim < hora_ini:
                    st.warning("🌙 Slot Noturno (Overnight)")

                st.divider()

                # B. O Calendário de Botões (Toggle)
                cal_matrix = calendar.monthcalendar(ano_sel, mes_idx)
                cols_h = st.columns(7)
                dias_sem = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
                for i, d in enumerate(dias_sem): 
                    cols_h[i].markdown(f"<div style='text-align:center; color: #888;'>{d}</div>", unsafe_allow_html=True)

                for semana in cal_matrix:
                    cols = st.columns(7)
                    for i, dia in enumerate(semana):
                        if dia != 0:
                            chave = f"{ano_sel}-{mes_idx:02d}-{dia:02d}"
                            
                            # Verifica se está marcado
                            is_selected = chave in st.session_state.dias_selecionados
                            
                            # Estilo visual
                            b_type = "primary" if is_selected else "secondary"
                            label = f"{dia}"
                            
                            if cols[i].button(label, key=f"cal_{chave}", type=b_type, use_container_width=True):
                                toggle_dia(ano_sel, mes_idx, dia)
                                st.rerun()
                        else:
                            cols[i].write("")

            # C. Ações de Salvar / Excluir
            st.write("")
            col_salvar, col_excluir = st.columns([3, 1])
            
            with col_salvar:
                label_save = "💾 Atualizar Bloco" if st.session_state.editing_block_id else "✅ Criar Bloco"
                if st.button(label_save, type="primary", use_container_width=True):
                    if not st.session_state.dias_selecionados:
                        st.error("Selecione dias no calendário!")
                    else:
                        # 1. Define ID do Bloco
                        if st.session_state.editing_block_id:
                            # Modo Edição: Mantém ID, remove slots antigos desse bloco da memória
                            block_id_final = st.session_state.editing_block_id
                            st.session_state.cache_slots = [
                                s for s in st.session_state.cache_slots 
                                if s['block_id'] != block_id_final
                            ]
                        else:
                            # Modo Criação: Novo ID
                            block_id_final = str(uuid.uuid4())

                        # 2. Gera novos slots
                        is_overnight = hora_fim < hora_ini
                        novos_slots = []
                        
                        for str_dt in sorted(st.session_state.dias_selecionados):
                            dt_base = datetime.strptime(str_dt, "%Y-%m-%d")
                            ini = datetime.combine(dt_base, hora_ini)
                            fim = datetime.combine(dt_base + timedelta(days=1 if is_overnight else 0), hora_fim)
                            
                            novos_slots.append({
                                "id": str(uuid.uuid4()),
                                "notam_id": st.session_state.notam_ativo,
                                "block_id": block_id_final,
                                "start": ini.isoformat(),
                                "end": fim.isoformat()
                            })
                        
                        # 3. Atualiza Cache e Salva no Banco
                        st.session_state.cache_slots.extend(novos_slots)
                        db_manager.salvar_slots_manuais(st.session_state.notam_ativo, st.session_state.cache_slots)
                        
                        st.success("Salvo com sucesso!")
                        limpar_editor() # Reseta para modo 'Novo'
                        st.rerun()

            with col_excluir:
                # Só mostra botão excluir se estiver editando
                if st.session_state.editing_block_id:
                    if st.button("🗑️ Excluir", type="secondary", use_container_width=True):
                        # Remove slots do bloco
                        b_id = st.session_state.editing_block_id
                        st.session_state.cache_slots = [
                            s for s in st.session_state.cache_slots 
                            if s['block_id'] != b_id
                        ]
                        # Salva alteração (remoção)
                        db_manager.salvar_slots_manuais(st.session_state.notam_ativo, st.session_state.cache_slots)
                        limpar_editor()
                        st.rerun()

# --------------------------------------------------------------------------
# ABA 2: VISÃO GERAL (Tabela Simples)
# --------------------------------------------------------------------------
with tab_cronograma:
    st.info("Aqui será exibido o cronograma consolidado de todos os NOTAMs.")
    # Implementação futura de Gantt ou Tabela Geral