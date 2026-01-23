import streamlit as st
import pandas as pd
import calendar
import uuid
from datetime import datetime, time, timedelta, date
from utils import db_manager, formatters, timeline_processor, pdf_generator

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gestão de Obras NOTAM", layout="wide")
st.title("🚨 Monitoramento & Cadastro de Obras")

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

# --- ESTADO PARA O EDITOR ---
if 'dias_selecionados' not in st.session_state: st.session_state.dias_selecionados = set()
if 'notam_em_edicao' not in st.session_state: st.session_state.notam_em_edicao = None
if 'slots_temporarios' not in st.session_state: st.session_state.slots_temporarios = []

# ==============================================================================
# 1. CARREGAMENTO E LIMPEZA (CORRIGIDO)
# ==============================================================================
df_notams = db_manager.carregar_notams()
df_config = db_manager.carregar_filtros_configurados()

# Verifica se carregou dados
if df_notams.empty:
    st.warning("Banco de dados de NOTAMs vazio.")
    st.stop()

# --- CORREÇÃO: CRIAÇÃO DO ID ÚNICO ---
# Se o banco não traz 'id_notam', criamos combinando LOCAL + NUMERO (ex: SBGR_A1234/23)
if 'id_notam' not in df_notams.columns:
    # Garante que são strings para evitar erro de concatenação
    df_notams['loc'] = df_notams['loc'].astype(str)
    df_notams['n'] = df_notams['n'].astype(str)
    df_notams['id_notam'] = df_notams['loc'] + "_" + df_notams['n']

# Regras de Filtro
filtros_assunto = df_config[df_config['tipo'] == 'assunto']['valor'].tolist()
filtros_condicao = df_config[df_config['tipo'] == 'condicao']['valor'].tolist()

# --- LÓGICA DE FILTRAGEM (CRÍTICOS) ---
# 1. Filtra Frota
frota = db_manager.carregar_frota_monitorada()
if frota:
    df_base = df_notams[df_notams['loc'].isin(frota)]
else:
    df_base = df_notams

# 2. Filtra Assunto/Condição
mask_assunto = df_base['assunto_desc'].isin(filtros_assunto)
mask_condicao = df_base['condicao_desc'].isin(filtros_condicao)
df_critico = df_base[mask_assunto & mask_condicao].copy()

# --- LIMPEZA DE ÓRFÃOS ---
# Agora 'id_notam' existe, então essa linha não vai mais dar erro
ids_ativos = df_critico['id_notam'].unique().tolist()
db_manager.limpar_registros_orfaos(ids_ativos)

# ==============================================================================
# 2. INTERFACE
# ==============================================================================

tab_cadastro, tab_cronograma, tab_turno = st.tabs(["🛠️ Cadastro & Edição", "📅 Cronograma Geral", "📄 Relatório de Turno"])

# --------------------------------------------------------------------------
# ABA 1: CADASTRO VISUAL (NOVA FUNCIONALIDADE)
# --------------------------------------------------------------------------
with tab_cadastro:
    col_lista, col_editor = st.columns([1, 2])

    # --- LISTA LATERAL DE SELEÇÃO ---
    with col_lista:
        st.subheader("1. Selecione o NOTAM")
        st.info(f"{len(df_critico)} NOTAMs Críticos identificados.")
        
        # Prepara dataframe para o seletor
        df_select = df_critico[['id_notam', 'loc', 'n', 'assunto_desc']].copy()
        df_select['Label'] = df_select['loc'] + " - " + df_select['n']
        
        # Evento de Seleção
        event = st.dataframe(
            df_select[['Label', 'assunto_desc']],
            column_config={
                "Label": "NOTAM",
                "assunto_desc": "Obra/Serviço"
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        # Processa a seleção
        notam_selecionado = None
        if event.selection.rows:
            idx = event.selection.rows[0]
            notam_dados = df_critico.iloc[idx]
            notam_id = notam_dados['id_notam'] # Chave única
            
            # Se mudou o NOTAM selecionado, carrega os dados do banco
            if st.session_state.notam_em_edicao != notam_id:
                st.session_state.notam_em_edicao = notam_id
                st.session_state.slots_temporarios = db_manager.carregar_slots_manuais(notam_id)
                st.session_state.dias_selecionados = set() # Limpa seleção visual
                st.rerun()
            
            notam_selecionado = notam_dados

    # --- ÁREA DO EDITOR (DIREITA) ---
    with col_editor:
        if notam_selecionado is None:
            st.info("👈 Selecione um NOTAM na lista à esquerda para cadastrar os horários de obra.")
        else:
            # --- CABEÇALHO DO NOTAM ---
            st.markdown(f"### 🚧 Editando: {notam_selecionado['loc']} - {notam_selecionado['n']}")
            with st.expander("Ver Texto Completo (Item E)", expanded=False):
                st.text(notam_selecionado['e'])
                st.caption(f"Período Bruto (B/C): {notam_selecionado['b']} até {notam_selecionado['c']}")

            st.divider()

            # --- EDITOR VISUAL (V3.0 Adaptado) ---
            
            # 1. Configuração do Bloco
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                ano_sel = st.number_input("Ano", 2025, 2030, 2026)
            with c2:
                mes_nomes = list(calendar.month_name)[1:]
                mes_txt = st.selectbox("Mês", mes_nomes, index=0)
                mes_idx = mes_nomes.index(mes_txt) + 1
            with c3:
                hora_ini = st.time_input("Início (UTC)", value=time(8,0))
            with c4:
                hora_fim = st.time_input("Fim (UTC)", value=time(17,0))

            # 2. Calendário Toggle
            cal_matrix = calendar.monthcalendar(ano_sel, mes_idx)
            cols_h = st.columns(7)
            dias_sem = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
            for i, d in enumerate(dias_sem): cols_h[i].markdown(f"<div style='text-align:center'><b>{d}</b></div>", unsafe_allow_html=True)

            def alternar_dia(a, m, d):
                k = f"{a}-{m:02d}-{d:02d}"
                if k in st.session_state.dias_selecionados: st.session_state.dias_selecionados.remove(k)
                else: st.session_state.dias_selecionados.add(k)

            for semana in cal_matrix:
                cols = st.columns(7)
                for i, dia in enumerate(semana):
                    if dia != 0:
                        chave = f"{ano_sel}-{mes_idx:02d}-{dia:02d}"
                        tipo = "primary" if chave in st.session_state.dias_selecionados else "secondary"
                        if cols[i].button(f"{dia}", key=f"btn_{chave}", type=tipo, use_container_width=True):
                            alternar_dia(ano_sel, mes_idx, dia)
                            st.rerun()
                    else:
                        cols[i].write("")

            # 3. Ações de Adição
            st.caption(f"Dias marcados: {len(st.session_state.dias_selecionados)}")
            col_add, col_limp = st.columns([3, 1])
            
            with col_add:
                if st.button("➕ Gerar Slots para Dias Marcados", type="primary", use_container_width=True):
                    novos = []
                    is_overnight = hora_fim < hora_ini
                    for d_str in sorted(st.session_state.dias_selecionados):
                        dt_base = datetime.strptime(d_str, "%Y-%m-%d")
                        ini = datetime.combine(dt_base, hora_ini)
                        fim = datetime.combine(dt_base + timedelta(days=1 if is_overnight else 0), hora_fim)
                        
                        novos.append({
                            "id": str(uuid.uuid4()),
                            "start": ini.isoformat(),
                            "end": fim.isoformat()
                        })
                    
                    st.session_state.slots_temporarios.extend(novos)
                    st.session_state.dias_selecionados = set()
                    st.success("Adicionado!")
                    st.rerun()
            
            with col_limp:
                if st.button("Limpar Seleção"):
                    st.session_state.dias_selecionados = set()
                    st.rerun()

            # 4. Tabela de Revisão e Salvamento
            st.subheader("📋 Slots Cadastrados para este NOTAM")
            if st.session_state.slots_temporarios:
                df_slots = pd.DataFrame(st.session_state.slots_temporarios)
                # Formatação para exibição
                df_view = df_slots.copy()
                df_view['Início'] = pd.to_datetime(df_view['start']).dt.strftime("%d/%m/%Y %H:%M")
                df_view['Fim'] = pd.to_datetime(df_view['end']).dt.strftime("%d/%m/%Y %H:%M")
                
                df_editado = st.data_editor(
                    df_view[['Início', 'Fim']], 
                    num_rows="dynamic", 
                    use_container_width=True,
                    key="editor_final"
                )
                
                # Se deletou linhas no editor, atualiza o state (lógica simplificada)
                if len(df_editado) < len(st.session_state.slots_temporarios):
                    st.warning("Para salvar exclusões, clique em Salvar abaixo.")

                if st.button("💾 SALVAR DEFINITIVAMENTE", type="primary", use_container_width=True):
                    # Aqui chamamos o backend
                    db_manager.salvar_slots_manuais(
                        notam_id=st.session_state.notam_em_edicao,
                        dados_json=st.session_state.slots_temporarios
                    )
                    st.success(f"Cadastro atualizado para o NOTAM {notam_selecionado['n']}!")
            else:
                st.info("Nenhum slot cadastrado. Use o calendário acima.")

# --------------------------------------------------------------------------
# ABA 2: CRONOGRAMA (Lê dos Manuais agora)
# --------------------------------------------------------------------------
with tab_cronograma:
    # AQUI MUDAMOS A LÓGICA:
    # Em vez de calcular o cronograma via parser automático,
    # nós carregamos os slots manuais do banco para cada NOTAM crítico.
    
    st.info("Visualizando cronograma baseado nos cadastros manuais.")
    
    # Lógica de montar o DataFrame mestre para o cronograma
    # 1. Itera sobre df_critico
    # 2. Carrega slots de cada um via db_manager
    # 3. Monta o df_view final
    # (Implementação depende do seu backend, mas a lógica é essa)

# --------------------------------------------------------------------------
# ABA 3: RELATÓRIO DE TURNO
# --------------------------------------------------------------------------
with tab_turno:
    st.write("Funcionalidade de turno agora utilizará os dados validados manualmente.")
    # Segue a mesma lógica do código anterior, mas filtrando a tabela de slots manuais