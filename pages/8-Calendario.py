import streamlit as st
import pandas as pd
import calendar
import uuid
from datetime import datetime, time, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editor NOTAM Avançado", layout="wide")

# --- ESTADO DA SESSÃO ---
if 'all_slots' not in st.session_state:
    # Lista mestra de dicionários: {'id', 'block_id', 'start', 'end'}
    st.session_state.all_slots = []

if 'dias_selecionados' not in st.session_state:
    st.session_state.dias_selecionados = set() # Formato "YYYY-MM-DD"

if 'editing_block_id' not in st.session_state:
    st.session_state.editing_block_id = None # Se None, modo CRIAÇÃO. Se preenchido, modo EDIÇÃO.

# --- FUNÇÕES DE LÓGICA ---

def limpar_selecao():
    st.session_state.dias_selecionados = set()
    st.session_state.editing_block_id = None

def alternar_dia(ano, mes, dia):
    chave = f"{ano}-{mes:02d}-{dia:02d}"
    if chave in st.session_state.dias_selecionados:
        st.session_state.dias_selecionados.remove(chave)
    else:
        st.session_state.dias_selecionados.add(chave)

def carregar_bloco_para_edicao(block_id):
    """Recupera os dados de um bloco e preenche a UI"""
    # Filtra slots desse bloco
    slots = [s for s in st.session_state.all_slots if s['block_id'] == block_id]
    
    if not slots:
        return

    # Limpa seleção atual
    st.session_state.dias_selecionados = set()
    
    # Reconstrói os dias selecionados (set)
    for s in slots:
        # Extrai a data do início
        str_data = s['start'].strftime("%Y-%m-%d")
        st.session_state.dias_selecionados.add(str_data)
    
    # Define o ID que estamos editando
    st.session_state.editing_block_id = block_id
    
    # Para a UI, precisamos pegar o horário e o Mês/Ano do primeiro slot para focar o calendário
    primeiro_slot = slots[0]
    
    # Salvamos em session state temporário para os widgets lerem
    st.session_state['_edit_hora_ini'] = primeiro_slot['start'].time()
    st.session_state['_edit_hora_fim'] = primeiro_slot['end'].time() if primeiro_slot['start'].date() == primeiro_slot['end'].date() else (primeiro_slot['end'] - timedelta(days=1)).time()
    # Se overnight, o fim é no dia seguinte, mas o horário hora:min é o que importa
    if primeiro_slot['end'].date() > primeiro_slot['start'].date():
         st.session_state['_edit_hora_fim'] = primeiro_slot['end'].time()

    st.session_state['_edit_ano'] = primeiro_slot['start'].year
    
    # Nome do mês para o selectbox
    nome_mes = calendar.month_name[primeiro_slot['start'].month]
    st.session_state['_edit_mes_nome'] = nome_mes

# --- LAYOUT PRINCIPAL ---

st.title("🛫 Gerenciador de Obras (Blocos)")

col_sidebar, col_main = st.columns([1, 3])

# ==============================================================================
# 1. SIDEBAR (LISTBOX DE BLOCOS)
# ==============================================================================
with col_sidebar:
    st.header("📂 Blocos Cadastrados")
    
    if st.button("✨ Novo Bloco (Limpar)", use_container_width=True):
        limpar_selecao()
        st.rerun()

    st.divider()

    if st.session_state.all_slots:
        # Agrupa slots por Block ID para mostrar no Listbox
        df_all = pd.DataFrame(st.session_state.all_slots)
        if not df_all.empty:
            # Pega resumo de cada bloco
            resumo = df_all.groupby('block_id').agg(
                qtd=('id', 'count'),
                inicio=('start', 'min'),
                fim=('start', 'max') # Pegamos o max start para saber o range de dias
            ).reset_index()
            
            # Ordena por data
            resumo = resumo.sort_values('inicio', ascending=True)

            for index, row in resumo.iterrows():
                b_id = row['block_id']
                data_ini_str = row['inicio'].strftime("%d/%m")
                data_fim_str = row['fim'].strftime("%d/%m")
                label = f"Bloco {str(b_id)[:4]}... | {data_ini_str} a {data_fim_str} ({row['qtd']} dias)"
                
                # Destaca se é o bloco sendo editado
                tipo_btn = "primary" if st.session_state.editing_block_id == b_id else "secondary"
                
                if st.button(label, key=f"sel_block_{b_id}", type=tipo_btn, use_container_width=True):
                    carregar_bloco_para_edicao(b_id)
                    st.rerun()
    else:
        st.info("Nenhum bloco cadastrado ainda.")

# ==============================================================================
# 2. ÁREA DE EDIÇÃO (CALENDÁRIO)
# ==============================================================================
with col_main:
    # Determina valores iniciais dos widgets
    # Se estiver editando, tenta pegar do state temporário, senão usa defaults
    
    def_ano = st.session_state.get('_edit_ano', 2026)
    def_mes_idx = 0
    if '_edit_mes_nome' in st.session_state:
        try:
            def_mes_idx = list(calendar.month_name)[1:].index(st.session_state['_edit_mes_nome'])
        except: pass
        
    def_h_ini = st.session_state.get('_edit_hora_ini', time(8, 0))
    def_h_fim = st.session_state.get('_edit_hora_fim', time(17, 0))

    # --- Header da Edição ---
    modo_texto = f"✏️ EDITANDO BLOCO {str(st.session_state.editing_block_id)[:8]}" if st.session_state.editing_block_id else "➕ CRIANDO NOVO BLOCO"
    st.subheader(modo_texto)

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ano_sel = st.number_input("Ano", min_value=2025, max_value=2030, value=def_ano)
        with c2:
            mes_nomes = list(calendar.month_name)[1:]
            mes_txt = st.selectbox("Mês", mes_nomes, index=def_mes_idx)
            mes_idx = mes_nomes.index(mes_txt) + 1
        with c3:
            hora_ini = st.time_input("Início (UTC)", value=def_h_ini)
        with c4:
            hora_fim = st.time_input("Fim (UTC)", value=def_h_fim)

        if hora_fim < hora_ini:
            st.warning("🌙 Overnight: O slot terminará no dia seguinte.")

    # --- Calendário Visual ---
    st.markdown(f"#### Selecione os dias em: **{mes_txt} / {ano_sel}**")
    
    cal_matrix = calendar.monthcalendar(ano_sel, mes_idx)
    dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    
    # Cabeçalho dias
    cols_h = st.columns(7)
    for i, d in enumerate(dias_semana):
        cols_h[i].markdown(f"<div style='text-align:center; font-weight:bold'>{d}</div>", unsafe_allow_html=True)
    
    # Grade
    for semana in cal_matrix:
        cols = st.columns(7)
        for i, dia_num in enumerate(semana):
            if dia_num == 0:
                cols[i].write("")
            else:
                chave_data = f"{ano_sel}-{mes_idx:02d}-{dia_num:02d}"
                # Verifica se está no set de selecionados
                marcado = chave_data in st.session_state.dias_selecionados
                btn_type = "primary" if marcado else "secondary"
                
                if cols[i].button(f"{dia_num}", key=f"btn_cal_{chave_data}", type=btn_type, use_container_width=True):
                    alternar_dia(ano_sel, mes_idx, dia_num)
                    st.rerun()

    # --- Rodapé de Ação ---
    st.divider()
    
    # Mostra dias selecionados (de todos os meses, não só do atual)
    total_dias = len(st.session_state.dias_selecionados)
    if total_dias > 0:
        st.write(f"**Total de dias marcados (geral):** {total_dias}")
    
    col_save, col_del = st.columns([4, 1])
    
    with col_save:
        label_btn = "💾 Salvar Alterações no Bloco" if st.session_state.editing_block_id else "✅ Criar Bloco"
        
        if st.button(label_btn, type="primary", use_container_width=True):
            if total_dias == 0:
                st.error("Selecione pelo menos um dia no calendário.")
            else:
                # 1. Define o ID do bloco (novo ou existente)
                if st.session_state.editing_block_id:
                    # Se editando, PRIMEIRO removemos todos os slots antigos desse bloco
                    bloco_atual = st.session_state.editing_block_id
                    st.session_state.all_slots = [s for s in st.session_state.all_slots if s['block_id'] != bloco_atual]
                else:
                    # Novo ID
                    bloco_atual = str(uuid.uuid4())

                # 2. Gera os novos slots baseados na seleção atual (set dias_selecionados)
                novos_slots = []
                is_overnight = hora_fim < hora_ini
                
                # Ordena para ficar organizado
                for data_str in sorted(list(st.session_state.dias_selecionados)):
                    dt_base = datetime.strptime(data_str, "%Y-%m-%d")
                    
                    inicio = datetime.combine(dt_base.date(), hora_ini)
                    if is_overnight:
                        fim = datetime.combine(dt_base.date() + timedelta(days=1), hora_fim)
                    else:
                        fim = datetime.combine(dt_base.date(), hora_fim)
                    
                    novos_slots.append({
                        'id': str(uuid.uuid4()),
                        'block_id': bloco_atual,
                        'start': inicio,
                        'end': fim
                    })
                
                # 3. Adiciona à lista mestra
                st.session_state.all_slots.extend(novos_slots)
                
                # 4. Limpeza
                st.success("Bloco salvo com sucesso!")
                limpar_selecao()
                # Remove variáveis temporárias de edição para não sujar o próximo novo
                for k in ['_edit_ano', '_edit_mes_nome', '_edit_hora_ini', '_edit_hora_fim']:
                    if k in st.session_state: del st.session_state[k]
                
                st.rerun()

    with col_del:
        if st.session_state.editing_block_id:
            if st.button("🗑️ Excluir Bloco", type="secondary", use_container_width=True):
                # Remove slots do bloco atual
                b_id = st.session_state.editing_block_id
                st.session_state.all_slots = [s for s in st.session_state.all_slots if s['block_id'] != b_id]
                limpar_selecao()
                st.success("Bloco excluído.")
                st.rerun()

# ==============================================================================
# 3. VISUALIZAÇÃO FINAL (TABELA GLOBAL)
# ==============================================================================
st.divider()
st.subheader("📋 Visão Geral de Todos os Slots")
if st.session_state.all_slots:
    df_final = pd.DataFrame(st.session_state.all_slots)
    df_final = df_final.sort_values('start')
    
    # Exibe tabela formatada
    st.dataframe(
        df_final[['start', 'end', 'block_id']],
        column_config={
            "start": st.column_config.DatetimeColumn("Início", format="DD/MM/YYYY HH:mm"),
            "end": st.column_config.DatetimeColumn("Fim", format="DD/MM/YYYY HH:mm"),
            "block_id": st.column_config.TextColumn("ID do Bloco", width="small")
        },
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("🚀 Confirmar e Enviar para Produção"):
        st.balloons()
        st.success(f"Enviando {len(df_final)} slots para o banco de dados...")
        # Aqui entra o código do Supabase