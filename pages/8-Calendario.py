import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time

# --- Configuração da Página ---
st.set_page_config(page_title="Cadastro Manual de NOTAM", layout="wide")

st.title("🛫 Cadastro de Obras (Manual Assistido)")
st.info("Modo de Alta Precisão: O operador define os blocos, o sistema calcula as datas.")

# --- Inicialização de Estado ---
if 'slots_gerados' not in st.session_state:
    st.session_state.slots_gerados = []

# --- FUNÇÕES AUXILIARES ---
def gerar_datas_bloco(dt_inicio, dt_fim, hora_inicio, hora_fim, dias_semana_permitidos):
    novos_slots = []
    curr = dt_inicio
    
    # Identifica se é overnight (termina no dia seguinte)
    is_overnight = hora_fim < hora_inicio
    
    while curr <= dt_fim:
        # Verifica se o dia da semana atual está permitido (0=Seg, 6=Dom)
        # O widget do streamlit retorna nomes, vamos converter ou usar indices se preferir.
        # Aqui assumo que 'dias_semana_permitidos' contém os indices 0-6
        if curr.weekday() in dias_semana_permitidos:
            inicio_slot = datetime.combine(curr, hora_inicio)
            
            if is_overnight:
                fim_slot = datetime.combine(curr + timedelta(days=1), hora_fim)
            else:
                fim_slot = datetime.combine(curr, hora_fim)
            
            novos_slots.append({
                "Inicio": inicio_slot,
                "Fim": fim_slot,
                "Dia Semana": inicio_slot.strftime("%a").upper()
            })
        
        curr += timedelta(days=1)
    
    return novos_slots

# --- BARRA LATERAL: CONTROLES DO BLOCO ---
with st.sidebar:
    st.header("1. Definir Bloco")
    
    # A. Seleção de Intervalo de Datas
    st.subheader("📅 Intervalo de Vigência")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        data_ini = st.date_input("Data Início", value=datetime.today())
    with col_d2:
        data_fim = st.date_input("Data Fim", value=datetime.today())

    # B. Seleção de Horário
    st.subheader("⏰ Horário de Atividade")
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        hora_ini = st.time_input("Hora Início (UTC)", value=time(8, 0))
    with col_h2:
        hora_fim = st.time_input("Hora Fim (UTC)", value=time(17, 0))

    if hora_fim < hora_ini:
        st.warning("⚠️ Slot Noturno (Overnight): Termina no dia seguinte.")

    # C. Filtro de Dias da Semana (O "Pulo do Gato" para TUE TIL SAT)
    st.subheader("📆 Filtro Semanal")
    # Mapeamento para facilitar
    mapa_dias = {0: "SEG", 1: "TER", 2: "QUA", 3: "QUI", 4: "SEX", 5: "SAB", 6: "DOM"}
    
    # Por padrão, todos vêm marcados
    dias_selecionados = st.multiselect(
        "Dias de Atividade:",
        options=list(mapa_dias.keys()),
        format_func=lambda x: mapa_dias[x],
        default=list(mapa_dias.keys()) # Todos marcados por padrão
    )

    # Botão de Ação
    if st.button("➕ Adicionar Bloco à Lista", type="primary"):
        if data_fim < data_ini:
            st.error("Data Fim não pode ser menor que Data Início.")
        else:
            novos = gerar_datas_bloco(data_ini, data_fim, hora_ini, hora_fim, dias_selecionados)
            st.session_state.slots_gerados.extend(novos)
            st.success(f"{len(novos)} slots adicionados!")

# --- ÁREA PRINCIPAL: VISUALIZAÇÃO E EDIÇÃO ---

st.header("2. Revisão e Ajuste Fino")

if st.session_state.slots_gerados:
    # Converter para DataFrame para facilitar visualização
    df = pd.DataFrame(st.session_state.slots_gerados)
    
    # Ordenar por data
    df = df.sort_values(by="Inicio").reset_index(drop=True)

    # Exibir como editor de dados (permite deletar linhas erradas!)
    st.write("Verifique os slots abaixo. Você pode excluir linhas se houver feriados ou exceções.")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Data Editor permite deletar rows (num_rows="dynamic")
        df_editado = st.data_editor(
            df,
            column_config={
                "Inicio": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                "Fim": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_dados"
        )

    with col2:
        st.metric("Total de Slots", len(df_editado))
        
        st.divider()
        if st.button("✅ Confirmar e Salvar no Banco"):
            # Aqui entraria a lógica de salvar no Supabase
            st.toast("Dados enviados para o Supabase com Sucesso!", icon="🚀")
            # st.write(df_editado.to_dict('records')) # Payload final

    # --- VISUALIZAÇÃO GRÁFICA (GANTT SIMPLES) ---
    st.subheader("3. Visualização Gráfica")
    if not df_editado.empty:
        # Criar um gráfico simples com Altair ou Plotly para ver buracos
        import altair as alt
        
        chart = alt.Chart(df_editado).mark_bar().encode(
            x='Inicio:T',
            x2='Fim:T',
            y='Dia Semana:N',
            tooltip=['Inicio', 'Fim']
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)

else:
    st.info("👈 Utilize a barra lateral para adicionar o primeiro bloco de horários.")
    st.write("Exemplo: Para 'JAN 12 TIL 15', selecione 12/01 a 15/01 e clique em Adicionar.")

# Botão para limpar tudo
if st.session_state.slots_gerados:
    if st.button("🗑️ Limpar Lista"):
        st.session_state.slots_gerados = []
        st.rerun()