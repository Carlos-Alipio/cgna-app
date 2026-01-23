import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, time, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editor Visual NOTAM", layout="centered")

st.title("🗓️ Cadastro Visual (Toque para Selecionar)")
st.caption("Clique nos dias para marcar/desmarcar. O botão fica vermelho quando selecionado.")

# --- ESTADO DA SESSÃO ---
# Armazena os dias selecionados no formato "YYYY-MM-DD"
if 'dias_selecionados' not in st.session_state:
    st.session_state.dias_selecionados = set()

if 'slots_agendados' not in st.session_state:
    st.session_state.slots_agendados = []

# --- FUNÇÃO DE TOGGLE ---
def alternar_dia(ano, mes, dia):
    """Liga ou desliga um dia na seleção"""
    chave_data = f"{ano}-{mes:02d}-{dia:02d}"
    if chave_data in st.session_state.dias_selecionados:
        st.session_state.dias_selecionados.remove(chave_data)
    else:
        st.session_state.dias_selecionados.add(chave_data)

# --- 1. CONFIGURAÇÃO DO BLOCO ---
with st.container(border=True):
    st.subheader("1. Parâmetros")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        ano_sel = st.number_input("Ano", min_value=2025, max_value=2030, value=2026)
    with c2:
        mes_nomes = list(calendar.month_name)[1:]
        mes_txt = st.selectbox("Mês", mes_nomes, index=0) # Jan
        mes_idx = mes_nomes.index(mes_txt) + 1
    with c3:
        hora_ini = st.time_input("Início (UTC)", value=time(3, 40))
    with c4:
        hora_fim = st.time_input("Fim (UTC)", value=time(7, 50))

    if hora_fim < hora_ini:
        st.warning(f"🌙 Overnight: O slot termina no dia seguinte.")

# --- 2. O CALENDÁRIO COM BOTÕES (TOGGLE) ---
st.subheader(f"2. Toque nos dias de {mes_txt}/{ano_sel}")

cal_matrix = calendar.monthcalendar(ano_sel, mes_idx)
dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]

# Cabeçalho
cols = st.columns(7)
for i, dia in enumerate(dias_semana):
    cols[i].markdown(f"<div style='text-align: center; font-weight: bold;'>{dia}</div>", unsafe_allow_html=True)

# Grade de Botões
for semana in cal_matrix:
    cols = st.columns(7)
    for i, dia_num in enumerate(semana):
        if dia_num == 0:
            cols[i].write("") # Espaço vazio
        else:
            # Verifica se está marcado
            chave_atual = f"{ano_sel}-{mes_idx:02d}-{dia_num:02d}"
            esta_marcado = chave_atual in st.session_state.dias_selecionados
            
            # Estilo do botão: "primary" (vermelho/destaque) se marcado, "secondary" (cinza) se não
            tipo_btn = "primary" if esta_marcado else "secondary"
            
            # O botão funciona como um callback
            if cols[i].button(f"{dia_num}", key=f"btn_{chave_atual}", type=tipo_btn, use_container_width=True):
                alternar_dia(ano_sel, mes_idx, dia_num)
                st.rerun() # Recarrega para atualizar a cor instantaneamente

# --- MOSTRAR SELEÇÃO ATUAL ---
total_selecionado = len([d for d in st.session_state.dias_selecionados if d.startswith(f"{ano_sel}-{mes_idx:02d}")])
if total_selecionado > 0:
    st.info(f"✅ {total_selecionado} dias marcados neste mês.")

# --- 3. AÇÃO DE CONFIRMAR ---
st.divider()

c_add, c_clear = st.columns([3, 1])

with c_add:
    if st.button("➕ Gerar Slots para os Dias Marcados", type="primary", use_container_width=True):
        if not st.session_state.dias_selecionados:
            st.error("Nenhum dia selecionado no total!")
        else:
            novos_slots = []
            is_overnight = hora_fim < hora_ini
            
            # Ordena as datas para ficar bonito
            datas_ordenadas = sorted(list(st.session_state.dias_selecionados))
            
            for str_data in datas_ordenadas:
                # Converte string de volta para data
                dt_base = datetime.strptime(str_data, "%Y-%m-%d")
                
                # Monta os slots
                dt_inicio = datetime.combine(dt_base.date(), hora_ini)
                
                if is_overnight:
                    dt_fim = datetime.combine(dt_base.date() + timedelta(days=1), hora_fim)
                else:
                    dt_fim = datetime.combine(dt_base.date(), hora_fim)
                
                novos_slots.append({
                    "Inicio": dt_inicio,
                    "Fim": dt_fim,
                    "Dia": dt_inicio.strftime("%d/%m/%Y"),
                    "Semana": dt_inicio.strftime("%a").upper()
                })
            
            st.session_state.slots_agendados.extend(novos_slots)
            # Limpa a seleção após adicionar (opcional, mas bom fluxo)
            st.session_state.dias_selecionados = set() 
            st.success(f"{len(novos_slots)} slots gerados com sucesso!")
            st.rerun()

with c_clear:
    if st.button("Limpar Seleção"):
        st.session_state.dias_selecionados = set()
        st.rerun()

# --- 4. TABELA FINAL ---
if st.session_state.slots_agendados:
    st.subheader("📋 Lista Final de Slots")
    
    df = pd.DataFrame(st.session_state.slots_agendados)
    df = df.sort_values(by="Inicio").reset_index(drop=True)
    
    # Editor final (permite deletar linhas se errou)
    df_final = st.data_editor(
        df,
        column_config={
            "Inicio": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
            "Fim": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
        },
        use_container_width=True,
        num_rows="dynamic"
    )
    
    if st.button("🚀 Enviar Definitivo para Supabase", use_container_width=True):
        st.toast("Enviando dados...", icon="⏳")
        # Coloque aqui sua função de insert no Supabase
        # supabase.table('notams').insert(df_final.to_dict('records')).execute()
        st.success("Dados salvos com sucesso!")
        st.balloons()