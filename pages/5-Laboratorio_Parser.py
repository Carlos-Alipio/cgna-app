import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parser_notam, casos_reais

st.set_page_config(page_title="Lab Parser Blindado", layout="wide")

st.title("🛡️ Laboratório com Regressão Automática")

# ==============================================================================
# 0. FUNÇÃO AUXILIAR DE CONVERSÃO DE INPUT
# ==============================================================================
def converter_input_para_raw(texto_input):
    if not texto_input: return ""
    limpo = ''.join(filter(str.isdigit, str(texto_input)))
    if len(limpo) == 12: # DDMMYYYYHHMM
        dia = limpo[0:2]
        mes = limpo[2:4]
        ano = limpo[6:8]
        hora = limpo[8:12]
        return f"{ano}{mes}{dia}{hora}"
    elif len(limpo) == 10: # YYMMDDHHMM
        return limpo
    return limpo

# ==============================================================================
# 1. MOTOR DE REGRESSÃO
# ==============================================================================
st.sidebar.header("🚦 Status da Regressão")
falhas = []
sucessos = 0

for caso in casos_reais.CASOS_BLINDADOS:
    try:
        slots = parser_notam.interpretar_periodo_atividade(
            caso['d'], "TESTE", caso['b'], caso['c']
        )
        qtd_atual = len(slots)
        
        # Formatação segura para evitar erros em listas vazias
        if qtd_atual > 0:
            primeiro_ini = slots[0]['inicio'].strftime("%d/%m/%Y %H:%M")
            # Ordena para garantir que pegamos o último cronológico
            slots_sorted = sorted(slots, key=lambda x: x['fim'])
            ultimo_fim = slots_sorted[-1]['fim'].strftime("%d/%m/%Y %H:%M")
        else:
            primeiro_ini = "N/A"
            ultimo_fim = "N/A"
            
        esp = caso['esperado']
        erros_caso = []
        
        if qtd_atual != esp['qtd_slots']:
            erros_caso.append(f"Qtd: {esp['qtd_slots']} vs {qtd_atual}")
        if primeiro_ini != esp['primeiro_inicio']:
            erros_caso.append(f"1º: {esp['primeiro_inicio']} vs {primeiro_ini}")
        if ultimo_fim != esp['ultimo_fim']:
            erros_caso.append(f"Último: {esp['ultimo_fim']} vs {ultimo_fim}")
            
        if erros_caso:
            falhas.append(f"❌ **{caso['id']}**: " + " | ".join(erros_caso))
        else:
            sucessos += 1
            
    except Exception as e:
        falhas.append(f"🔥 **{caso['id']}**: Erro - {str(e)}")

if len(falhas) > 0:
    st.error(f"🚨 PARE! Regressão falhou em {len(falhas)} caso(s)!")
    for f in falhas: st.markdown(f)
    st.sidebar.error("FALHA CRÍTICA")
else:
    st.success(f"✅ Sistema Estável ({sucessos} casos OK).")
    st.sidebar.success("SISTEMA ONLINE")

st.divider()

# ==============================================================================
# 2. ÁREA DE TESTE
# ==============================================================================
st.subheader("🔬 Testar Novo Caso")

col_b, col_c = st.columns(2)
with col_b:
    input_b = st.text_input("Início (B)", placeholder="Ex: 30/12/2025 18:09")
    raw_b = converter_input_para_raw(input_b)
    if raw_b: st.caption(f"Interpretado: `{raw_b}`")

with col_c:
    input_c = st.text_input("Fim (C)", placeholder="Ex: 30/03/2026 09:00")
    raw_c = converter_input_para_raw(input_c)
    if raw_c: st.caption(f"Interpretado: `{raw_c}`")

texto_d = st.text_area("Texto Item D:", height=100)

if st.button("Processar", type="primary"):
    if not raw_b or not raw_c:
        st.warning("Preencha as datas B e C.")
    else:
        try:
            slots = parser_notam.interpretar_periodo_atividade(texto_d, "TESTE", raw_b, raw_c)
            
            if not slots:
                st.warning("Nenhum slot gerado.")
            else:
                df = pd.DataFrame(slots)
                df = df.sort_values('inicio')
                
                # Dados para Copiar/Colar no JSON
                p_ini = df.iloc[0]['inicio'].strftime('%d/%m/%Y %H:%M')
                u_fim = df.iloc[-1]['fim'].strftime('%d/%m/%Y %H:%M')
                
                st.info("👇 **Snippet JSON:**")
                st.code(f"""
    {{
        "id": "CASO_NOVO",
        "desc": "...",
        "b": "{raw_b}",
        "c": "{raw_c}",
        "d": "{texto_d}",
        "esperado": {{
            "qtd_slots": {len(slots)},
            "primeiro_inicio": "{p_ini}",
            "ultimo_fim": "{u_fim}"
        }}
    }},""", language="python")
                
                # --- VISUALIZAÇÃO INTELIGENTE (A Correção) ---
                df['Dia'] = df['inicio'].dt.strftime('%d/%m/%Y (%a)')
                df['Início'] = df['inicio'].dt.strftime('%H:%M')
                
                # Função para formatar o FIM: Mostra data se for dia diferente
                def formatar_fim(row):
                    if row['inicio'].date() == row['fim'].date():
                        return row['fim'].strftime('%H:%M')
                    else:
                        # Destaca a data final se for diferente da inicial
                        return row['fim'].strftime('%d/%m/%Y %H:%M')
                
                df['Fim'] = df.apply(formatar_fim, axis=1)
                
                st.metric("Slots Gerados", len(df))
                st.dataframe(df[['Dia', 'Início', 'Fim']], use_container_width=True, height=400)
                
        except Exception as e:
            st.error(f"Erro: {e}")