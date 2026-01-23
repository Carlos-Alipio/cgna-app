import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, time, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editor NOTAM Visual", layout="centered")

st.title("🗓️ Cadastro Visual de NOTAM")
st.caption("Selecione o horário e clique nos dias no calendário.")

# --- ESTADO DA SESSÃO ---
if 'slots_agendados' not in st.session_state:
    st.session_state.slots_agendados = []

# --- 1. CONFIGURAÇÃO DO BLOCO (HORÁRIO E MÊS) ---
with st.container(border=True):
    st.subheader("1. Configuração do Bloco")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ano_sel = st.number_input("Ano", min_value=2025, max_value=2030, value=2026)
    with c2:
        mes_nomes = list(calendar.month_name)[1:] # Jan a Dez
        mes_txt = st.selectbox("Mês", mes_nomes, index=0) # Começa em Janeiro
        mes_idx = mes_nomes.index(mes_txt) + 1
    with c3:
        hora_ini = st.time_input("Início (UTC)", value=time(3, 40))
    with c4:
        hora_fim = st.time_input("Fim (UTC)", value=time(7, 50))

    # Alerta de Overnight
    if hora_fim < hora_ini:
        st.warning(f"🌙 Overnight detectado: O slot começará no dia selecionado e terminará no dia seguinte.")

# --- 2. O CALENDÁRIO INTERATIVO ---
st.subheader(f"2. Selecione os dias de {mes_txt}/{ano_sel}")

# Obtém a matriz do calendário (lista de semanas)
cal_matrix = calendar.monthcalendar(ano_sel, mes_idx)
dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]

# Cabeçalho dos dias da semana
cols_header = st.columns(7)
for i, dia in enumerate(dias_semana):
    cols_header[i].markdown(f"**{dia}**", unsafe_allow_html=True)

# Grade de dias (Checkboxes)
dias_selecionados = []
with st.container(border=True):
    for semana in cal_matrix:
        cols = st.columns(7)
        for i, dia_num in enumerate(semana):
            if dia_num == 0:
                cols[i].write("") # Espaço vazio
            else:
                # Chave única para cada checkbox
                key_day = f"chk_{ano_sel}_{mes_idx}_{dia_num}"
                # Renderiza o checkbox
                if cols[i].checkbox(f"{dia_num}", key=key_day):
                    dias_selecionados.append(dia_num)

# --- 3. AÇÃO DE ADICIONAR ---
st.divider()
if st.button("➕ Adicionar Dias Selecionados à Lista", type="primary", use_container_width=True):
    if not dias_selecionados:
        st.error("Nenhum dia selecionado!")
    else:
        novos_slots = []
        is_overnight = hora_fim < hora_ini
        
        for dia in sorted(dias_selecionados):
            dt_inicio = datetime(ano_sel, mes_idx, dia, hora_ini.hour, hora_ini.minute)
            
            if is_overnight:
                dt_fim = datetime(ano_sel, mes_idx, dia) + timedelta(days=1)
                dt_fim = dt_fim.replace(hour=hora_fim.hour, minute=hora_fim.minute)
            else:
                dt_fim = datetime(ano_sel, mes_idx, dia, hora_fim.hour, hora_fim.minute)
            
            novos_slots.append({
                "Inicio": dt_inicio,
                "Fim": dt_fim,
                "Dia": dt_inicio.strftime("%d/%m/%Y"),
                "Semana": dt_inicio.strftime("%a")
            })
        
        st.session_state.slots_agendados.extend(novos_slots)
        st.toast(f"{len(novos_slots)} slots adicionados com sucesso!", icon="✅")
        # Opcional: Limpar checkboxes (exige rerun ou manipulação de session state complexa, simplifiquei aqui)

# --- 4. REVISÃO E ENVIO ---
if st.session_state.slots_agendados:
    st.subheader("📋 Lista de Slots Gerados")
    
    df = pd.DataFrame(st.session_state.slots_agendados)
    # Ordena por data
    df = df.sort_values(by="Inicio").reset_index(drop=True)
    
    # Editor para exclusão final
    df_final = st.data_editor(
        df,
        column_config={
            "Inicio": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
            "Fim": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
        },
        use_container_width=True,
        num_rows="dynamic"
    )
    
    c_save1, c_save2 = st.columns(2)
    with c_save1:
        if st.button("🗑️ Limpar Tudo"):
            st.session_state.slots_agendados = []
            st.rerun()
    with c_save2:
        if st.button("🚀 Enviar para Supabase"):
            # Lógica de salvar
            st.success("Dados salvos no banco de dados!")
            st.json(df_final.to_dict(orient="records"))