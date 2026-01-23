import streamlit as st
import pandas as pd
import calendar
import uuid
from datetime import datetime, time, timedelta, date
from utils import db_manager, formatters, timeline_processor, pdf_generator

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gestão de Obras", layout="wide")
st.title("🚨 Monitoramento & Cadastro de Obras")

# --- CSS PARA MELHORAR A UI DO CALENDÁRIO ---
st.markdown("""
    <style>
    .stButton button {min-height: 45px;}
    div[data-testid="stExpander"] details summary p {font-size: 1.1rem; font-weight: 600;}
    </style>
""", unsafe_allow_html=True)

# --- ESTADOS DE SESSÃO ---
if 'dias_selecionados' not in st.session_state: st.session_state.dias_selecionados = set()
if 'notam_ativo' not in st.session_state: st.session_state.notam_ativo = None
if 'cache_slots' not in st.session_state: st.session_state.cache_slots = [] # Lista local de slots do NOTAM ativo

# ==============================================================================
# 1. CARREGAMENTO E PREPARAÇÃO DOS DADOS
# ==============================================================================
df_notams = db_manager.carregar_notams()
df_config = db_manager.carregar_filtros_configurados()

if df_notams.empty:
    st.warning("Banco de dados vazio.")
    st.stop()

# --- CORREÇÃO DO ERRO DE KEYERROR ---
# Cria a coluna ID se ela não existir
if 'id_notam' not in df_notams.columns:
    df_notams['loc'] = df_notams['loc'].astype(str)
    df_notams['n'] = df_notams['n'].astype(str)
    df_notams['id_notam'] = df_notams['loc'] + "_" + df_notams['n']

# Filtragem de Críticos
filtros_assunto = df_config[df_config['tipo'] == 'assunto']['valor'].tolist()
filtros_condicao = df_config[df_config['tipo'] == 'condicao']['valor'].tolist()

# 1. Filtro Frota
frota = db_manager.carregar_frota_monitorada()
df_base = df_notams[df_notams['loc'].isin(frota)] if frota else df_notams

# 2. Filtro Críticos
mask_assunto = df_base['assunto_desc'].isin(filtros_assunto)
mask_condicao = df_base['condicao_desc'].isin(filtros_condicao)
df_critico = df_base[mask_assunto & mask_condicao].copy()

# Limpeza de dados órfãos (Remove cadastros de NOTAMs que já expiraram)
ids_ativos = df_critico['id_notam'].unique().tolist()
db_manager.limpar_registros_orfaos(ids_ativos)

# ==============================================================================
# 2. INTERFACE
# ==============================================================================

tab_cadastro, tab_cronograma = st.tabs(["🛠️ Cadastro por Blocos", "📅 Visão Geral"])

# --------------------------------------------------------------------------
# ABA 1: CADASTRO VISUAL (MASTER-DETAIL)
# --------------------------------------------------------------------------
with tab_cadastro:
    col_lista, col_detalhe = st.columns([1, 2])

    # --- ESQUERDA: LISTA DE NOTAMS (MASTER) ---
    with col_lista:
        st.subheader("1. Selecione o NOTAM")
        st.caption("Lista de NOTAMs críticos ativos.")
        
        # Prepara tabela para seleção
        df_sel = df_critico[['id_notam', 'loc', 'n', 'assunto_desc']].copy()
        df_sel['Identificação'] = df_sel['loc'] + " " + df_sel['n']
        
        event = st.dataframe(
            df_sel[['Identificação', 'assunto_desc']],
            column_config={"assunto_desc": "Descrição"},
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            height=600
        )

        # Lógica de Seleção
        notam_selecionado = None
        if event.selection.rows:
            idx = event.selection.rows[0]
            notam_selecionado = df_critico.iloc[idx]
            id_atual = notam_selecionado['id_notam']

            # Se mudou o NOTAM, recarrega os dados do banco
            if st.session_state.notam_ativo != id_atual:
                st.session_state.notam_ativo = id_atual
                st.session_state.dias_selecionados = set() # Limpa calendário
                # Carrega slots salvos do banco para este NOTAM
                st.session_state.cache_slots = db_manager.carregar_slots_manuais(id_atual)
                st.rerun()

    # --- DIREITA: EDITOR DE BLOCOS (DETAIL) ---
    with col_detalhe:
        if notam_selecionado is None:
            st.info("👈 Selecione um NOTAM na lista ao lado para gerenciar seus horários.")
            st.stop()

        # Cabeçalho do NOTAM
        st.markdown(f"### 🚧 Gerenciando: {notam_selecionado['loc']} - {notam_selecionado['n']}")
        with st.expander("📖 Ler Texto do NOTAM", expanded=False):
            st.code(notam_selecionado['e'], language="text")
            st.caption(f"Vigência Oficial (Item B/C): {notam_selecionado['b']} até {notam_selecionado['c']}")

        st.divider()

        # ==================================================================
        # PARTE A: O CALENDÁRIO (CRIADOR DE BLOCOS)
        # ==================================================================
        st.subheader("2. Novo Bloco de Datas")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ano_sel = st.number_input("Ano", 2025, 2030, datetime.now().year)
        with c2:
            mes_nomes = list(calendar.month_name)[1:]
            mes_atual_idx = datetime.now().month - 1
            mes_txt = st.selectbox("Mês", mes_nomes, index=mes_atual_idx)
            mes_idx = mes_nomes.index(mes_txt) + 1
        with c3:
            hora_ini = st.time_input("Início (UTC)", value=time(8, 0))
        with c4:
            hora_fim = st.time_input("Fim (UTC)", value=time(17, 0))

        # Renderiza Calendário
        cal_matrix = calendar.monthcalendar(ano_sel, mes_idx)
        cols_h = st.columns(7)
        dias = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
        for i, d in enumerate(dias): cols_h[i].markdown(f"<div style='text-align:center'><b>{d}</b></div>", unsafe_allow_html=True)

        def toggle_dia(a, m, d):
            k = f"{a}-{m:02d}-{d:02d}"
            if k in st.session_state.dias_selecionados: st.session_state.dias_selecionados.remove(k)
            else: st.session_state.dias_selecionados.add(k)

        # Grade de Botões
        with st.container(border=True):
            for semana in cal_matrix:
                cols = st.columns(7)
                for i, dia in enumerate(semana):
                    if dia != 0:
                        chave = f"{ano_sel}-{mes_idx:02d}-{dia:02d}"
                        tipo = "primary" if chave in st.session_state.dias_selecionados else "secondary"
                        if cols[i].button(f"{dia}", key=f"btn_{chave}", type=tipo, use_container_width=True):
                            toggle_dia(ano_sel, mes_idx, dia)
                            st.rerun()
                    else:
                        cols[i].write("")
        
        # Ações do Calendário
        col_add, col_limpar = st.columns([3, 1])
        with col_add:
            label_btn = f"➕ Adicionar Bloco ({len(st.session_state.dias_selecionados)} dias selecionados)"
            if st.button(label_btn, type="primary", use_container_width=True):
                if not st.session_state.dias_selecionados:
                    st.error("Selecione dias no calendário!")
                else:
                    # CRIAÇÃO DO BLOCO
                    novo_block_id = str(uuid.uuid4()) # ID único para este grupo de datas
                    is_overnight = hora_fim < hora_ini
                    
                    novos_slots = []
                    for str_data in sorted(st.session_state.dias_selecionados):
                        dt_base = datetime.strptime(str_data, "%Y-%m-%d")
                        inicio = datetime.combine(dt_base, hora_ini)
                        fim = datetime.combine(dt_base + timedelta(days=1 if is_overnight else 0), hora_fim)
                        
                        novos_slots.append({
                            "id": str(uuid.uuid4()),
                            "notam_id": st.session_state.notam_ativo, # VINCULA AO NOTAM
                            "block_id": novo_block_id,                # VINCULA AO BLOCO
                            "start": inicio.isoformat(),
                            "end": fim.isoformat()
                        })
                    
                    # Adiciona à lista local e Salva no Banco
                    st.session_state.cache_slots.extend(novos_slots)
                    db_manager.salvar_slots_manuais(st.session_state.notam_ativo, st.session_state.cache_slots)
                    
                    st.session_state.dias_selecionados = set() # Limpa seleção
                    st.success("Bloco adicionado com sucesso!")
                    st.rerun()

        with col_limpar:
            if st.button("Limpar Seleção"):
                st.session_state.dias_selecionados = set()
                st.rerun()

        st.divider()

        # ==================================================================
        # PARTE B: LISTA DE BLOCOS CADASTRADOS (GESTÃO)
        # ==================================================================
        st.subheader(f"3. Blocos Cadastrados ({len(st.session_state.cache_slots)} slots totais)")

        if st.session_state.cache_slots:
            # Converte para DataFrame para agrupar
            df_slots = pd.DataFrame(st.session_state.cache_slots)
            df_slots['start_dt'] = pd.to_datetime(df_slots['start'])
            df_slots['end_dt'] = pd.to_datetime(df_slots['end'])
            
            # Agrupa por Block ID para mostrar resumido
            # Isso resolve o seu pedido: "blocos de datas para cada range"
            df_blocos = df_slots.groupby('block_id').agg(
                inicio_min=('start_dt', 'min'),
                inicio_max=('start_dt', 'max'),
                horario_str=('start_dt', lambda x: x.iloc[0].strftime('%H:%M UTC')),
                qtd_dias=('id', 'count')
            ).reset_index().sort_values('inicio_min')

            # Renderiza cada bloco como um Expander
            for idx, row in df_blocos.iterrows():
                b_id = row['block_id']
                periodo_str = f"{row['inicio_min'].strftime('%d/%b')} a {row['inicio_max'].strftime('%d/%b')}"
                titulo = f"📅 {periodo_str} | ⏰ {row['horario_str']} | ({row['qtd_dias']} dias)"
                
                with st.expander(titulo):
                    c_info, c_del = st.columns([4, 1])
                    with c_info:
                        st.write("Dias incluídos:")
                        # Mostra os dias deste bloco numa linha horizontal
                        dias_bloco = df_slots[df_slots['block_id'] == b_id]['start_dt'].dt.strftime('%d').tolist()
                        st.caption(", ".join(dias_bloco))
                    
                    with c_del:
                        if st.button("🗑️ Excluir Bloco", key=f"del_{b_id}"):
                            # Remove do cache local
                            st.session_state.cache_slots = [
                                s for s in st.session_state.cache_slots 
                                if s['block_id'] != b_id
                            ]
                            # Salva a nova lista no banco
                            db_manager.salvar_slots_manuais(st.session_state.notam_ativo, st.session_state.cache_slots)
                            st.rerun()
        else:
            st.info("Nenhum bloco cadastrado para este NOTAM ainda.")

# --------------------------------------------------------------------------
# ABA 2: VISUALIZAÇÃO GERAL
# --------------------------------------------------------------------------
with tab_cronograma:
    st.write("Visualização consolidada de todos os NOTAMs críticos.")
    # Aqui você pode carregar todos os slots de todos os notams críticos
    # e exibir num gráfico de Gantt ou tabela unificada.