import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parser_notam, casos_reais # Importa nosso cofre

st.set_page_config(page_title="Lab Parser Blindado", layout="wide")

st.title("🛡️ Laboratório com Regressão Automática")

# ==============================================================================
# 1. MOTOR DE REGRESSÃO (RODA AUTOMATICAMENTE)
# ==============================================================================
st.sidebar.header("🚦 Status da Regressão")

falhas = []
sucessos = 0

for caso in casos_reais.CASOS_BLINDADOS:
    try:
        # Roda o parser atual com os dados antigos
        slots = parser_notam.interpretar_periodo_atividade(
            caso['d'], "TESTE", caso['b'], caso['c']
        )
        
        # Cria o Snapshot do resultado atual
        qtd_atual = len(slots)
        if qtd_atual > 0:
            # Ordena para garantir comparação correta
            slots = sorted(slots, key=lambda x: x['inicio'])
            primeiro_ini = slots[0]['inicio'].strftime("%d/%m/%Y %H:%M")
            ultimo_fim = slots[-1]['fim'].strftime("%d/%m/%Y %H:%M")
        else:
            primeiro_ini = "N/A"
            ultimo_fim = "N/A"
            
        # COMPARAÇÃO (O momento da verdade)
        esp = caso['esperado']
        erros_caso = []
        
        if qtd_atual != esp['qtd_slots']:
            erros_caso.append(f"Qtd Slots: Esperado {esp['qtd_slots']} vs Gerado {qtd_atual}")
            
        if primeiro_ini != esp['primeiro_inicio']:
            erros_caso.append(f"1º Slot: Esperado {esp['primeiro_inicio']} vs Gerado {primeiro_ini}")
            
        if ultimo_fim != esp['ultimo_fim']:
            erros_caso.append(f"Último Slot: Esperado {esp['ultimo_fim']} vs Gerado {ultimo_fim}")
            
        if erros_caso:
            falhas.append(f"❌ **{caso['id']}**: " + " | ".join(erros_caso))
        else:
            sucessos += 1
            
    except Exception as e:
        falhas.append(f"🔥 **{caso['id']}**: Erro de execução - {str(e)}")

# EXIBE O SEMÁFORO
if len(falhas) > 0:
    st.error(f"🚨 PARE! O código atual QUEBROU {len(falhas)} caso(s) antigo(s)!")
    for f in falhas:
        st.markdown(f)
    st.sidebar.error("REGRESSÃO FALHOU")
else:
    st.success(f"✅ Sistema Estável: Todos os {sucessos} casos blindados estão funcionando.")
    st.sidebar.success("SISTEMA ÍNTEGRO")

st.divider()

# ==============================================================================
# 2. ÁREA DE TESTE DO NOVO CASO
# ==============================================================================
st.subheader("🔬 Testar Novo Caso")

c1, c2, c3 = st.columns(3)
with c1:
    dt_inicio = st.date_input("Data Início (B)", value=datetime.now())
    # ALTERADO: Campo Livre
    hr_inicio = st.text_input("Hora Início (B)", value="00:00", help="Ex: 0440 ou 04:40")
    
with c2:
    dt_fim = st.date_input("Data Fim (C)", value=datetime.now())
    # ALTERADO: Campo Livre
    hr_fim = st.text_input("Hora Fim (C)", value="23:59", help="Ex: 0750 ou 07:50")

with c3:
    # Tratamento para gerar o RAW corretamente independente se usar : ou não
    h_i_clean = hr_inicio.replace(":", "").strip().zfill(4)
    h_f_clean = hr_fim.replace(":", "").strip().zfill(4)
    
    raw_b = dt_inicio.strftime("%y%m%d") + h_i_clean
    raw_c = dt_fim.strftime("%y%m%d") + h_f_clean
    
    st.caption(f"Raw B: {raw_b}")
    st.caption(f"Raw C: {raw_c}")

texto_d = st.text_area("Texto Item D (Novo):", height=80)

if st.button("Processar Novo Caso", type="primary"):
    try:
        slots = parser_notam.interpretar_periodo_atividade(texto_d, "TESTE", raw_b, raw_c)
        
        if not slots:
            st.warning("Nenhum slot gerado.")
        else:
            df = pd.DataFrame(slots)
            df['Dia'] = df['inicio'].dt.strftime('%d/%m/%Y (%a)')
            df['Início'] = df['inicio'].dt.strftime('%H:%M')
            df['Fim'] = df['fim'].dt.strftime('%H:%M')
            
            # Ordena
            df = df.sort_values('inicio')
            
            # Resumo para "Blindagem"
            st.info("👇 Se este resultado estiver correto, adicione estes dados ao `casos_reais.py`:")
            code_snippet = f"""
    {{
        "id": "CASO_NOVO",
        "desc": "...",
        "b": "{raw_b}",
        "c": "{raw_c}",
        "d": "{texto_d}",
        "esperado": {{
            "qtd_slots": {len(slots)},
            "primeiro_inicio": "{df.iloc[0]['inicio'].strftime('%d/%m/%Y %H:%M')}",
            "ultimo_fim": "{df.iloc[-1]['fim'].strftime('%d/%m/%Y %H:%M')}"
        }}
    }},
            """
            st.code(code_snippet, language="python")
            
            st.metric("Slots Gerados", len(df))
            st.dataframe(df[['Dia', 'Início', 'Fim']], use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro: {e}")