import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import parser_notam

st.set_page_config(page_title="Validador de Regressão", layout="wide")
st.title("🛡️ Validador de Regressão (Parser NOTAM)")
st.markdown("Esta ferramenta testa o parser contra todos os casos críticos conhecidos simultaneamente.")

# ==============================================================================
# 1. DEFINIÇÃO DOS CASOS DE OURO (Baseado na sua imagem)
# ==============================================================================
CASOS_DE_OURO = [
    {
        "id": "LINHA_22_HERANCA",
        "desc": "Herança de DLY com múltiplos horários",
        "d": "DLY 1000-1030 2030-2100",
        "b": "2312232030", "c": "2603182100",
        "regra": "Deve gerar slots para AMBOS os horários (manhã e noite) todos os dias."
    },
    {
        "id": "LINHA_21_DIAS_SOLTOS",
        "desc": "Lista de dias numéricos soltos",
        "d": "JAN 20 23 27 30 1100-1900 JAN 22 1600-2200 JAN 24 1100-1600 JAN 29 1600-2100",
        "b": "2601201100", "c": "2601301900",
        "regra": "Deve identificar dias 20, 23, 27, 30 individualmente."
    },
    {
        "id": "LINHA_18_EVENTO_UNICO",
        "desc": "Evento único cruzando a noite (DEC 01/02)",
        "d": "DEC 01/02 2133-0115 DEC 02 TIL FEB 28 MON TUE THU 0745-1630...",
        "b": "2512012133", "c": "2602281630",
        "regra": "O dia 01/12 deve ter apenas UM slot iniciando às 21:33. Não pode haver slot iniciando dia 02 às 21:33."
    },
    {
        "id": "LINHA_13_COMPLEXO",
        "desc": "O Chefão: Dias soltos, Ranges, Meses e Herança Dupla",
        "d": "JAN 17 18 20 22 24 25 27 29 31 FEB 01 TIL 15 0340-0820 JAN 19 21 23 26 28 30 0340-0820 0915-1200",
        "b": "2601170340", "c": "2602150820",
        "regra": "JAN 19, 21... devem ter DOIS horários cada (0340 e 0915)."
    },
    {
        "id": "LINHA_11_WEEKDAY",
        "desc": "Range de Datas com Dias da Semana",
        "d": "JAN 10 TIL 16 TUE WED THU FRI SAT 0400-0759...",
        "b": "2601100400", "c": "2604100759",
        "regra": "Deve filtrar apenas os dias da semana citados dentro do intervalo de datas."
    },
    {
        "id": "LINHA_17_PERM",
        "desc": "Regra PERM (Sem texto)",
        "d": "PERM", # Simulando texto vazio ou PERM
        "b": "2512122117", "c": "PERM",
        "regra": "Data Final deve ser projectada para 365 dias."
    }
]

# ==============================================================================
# 2. MOTOR DE TESTES
# ==============================================================================

def executar_testes():
    resultados = []
    
    for caso in CASOS_DE_OURO:
        try:
            # Executa o Parser Atual
            slots = parser_notam.interpretar_periodo_atividade(
                caso['d'], "TESTE", caso['b'], caso['c']
            )
            
            # Análise Básica dos Resultados
            qtd_slots = len(slots)
            status = "❓ Analisar"
            cor = "gray"
            msg = ""

            # Validações Específicas (Regras de Negócio)
            if caso['id'] == "LINHA_22_HERANCA":
                # Verifica se temos slots começando com hora ~10 e hora ~20
                tem_manha = any(s['inicio'].hour == 10 for s in slots)
                tem_noite = any(s['inicio'].hour == 20 for s in slots)
                if tem_manha and tem_noite:
                    status = "✅ SUCESSO"
                    cor = "green"
                else:
                    status = "❌ FALHA"
                    cor = "red"
                    msg = f"Manhã: {tem_manha}, Noite: {tem_noite}"

            elif caso['id'] == "LINHA_18_EVENTO_UNICO":
                # Verifica o dia 02/12
                # Não deve ter início dia 02/12 às 21:33
                erros = [s for s in slots if s['inicio'].day == 2 and s['inicio'].month == 12 and s['inicio'].hour == 21]
                acerto = [s for s in slots if s['inicio'].day == 1 and s['inicio'].month == 12]
                
                if not erros and acerto:
                    status = "✅ SUCESSO"
                    cor = "green"
                else:
                    status = "❌ FALHA"
                    cor = "red"
                    msg = f"Slots errados no dia 02: {len(erros)}"

            elif caso['id'] == "LINHA_13_COMPLEXO":
                # Pega um dia de teste: JAN 19
                slots_jan19 = [s for s in slots if s['inicio'].day == 19 and s['inicio'].month == 1]
                # Esperamos 2 slots (0340 e 0915)
                if len(slots_jan19) >= 2:
                     status = "✅ SUCESSO"
                     cor = "green"
                else:
                     status = "❌ FALHA"
                     cor = "red"
                     msg = f"JAN 19 teve {len(slots_jan19)} slots (esperado >= 2)"
            
            elif caso['id'] == "LINHA_21_DIAS_SOLTOS":
                dias_encontrados = set(s['inicio'].day for s in slots if s['inicio'].month == 1)
                esperados = {20, 23, 27, 30}
                if esperados.issubset(dias_encontrados):
                    status = "✅ SUCESSO"
                    cor = "green"
                else:
                    status = "❌ FALHA"
                    cor = "red"
                    msg = f"Dias achados: {sorted(list(dias_encontrados))}"

            elif caso['id'] == "LINHA_17_PERM":
                # Verifica se o último slot está em 2026 (Dezembro)
                ultimo = slots[-1]['fim']
                if ultimo.year == 2026 and ultimo.month == 12:
                    status = "✅ SUCESSO"
                    cor = "green"
                else:
                    status = "❌ FALHA"
                    cor = "red"
                    msg = f"Data final: {ultimo}"

            else:
                if qtd_slots > 0:
                    status = "✅ OK (Gerou Dados)"
                    cor = "green"
                else:
                    status = "⚠️ VAZIO"
                    cor = "orange"

            resultados.append({
                "ID": caso['id'],
                "Descrição": caso['desc'],
                "Status": status,
                "Msg": msg,
                "Slots Gerados": qtd_slots,
                "Exemplo (1º Slot)": slots[0]['inicio'].strftime('%d/%m %H:%M') if slots else "-"
            })

        except Exception as e:
            resultados.append({
                "ID": caso['id'],
                "Descrição": caso['desc'],
                "Status": "🔥 ERRO CRÍTICO",
                "Msg": str(e),
                "Slots Gerados": 0,
                "Exemplo (1º Slot)": "-"
            })
    
    return pd.DataFrame(resultados)

# ==============================================================================
# 3. INTERFACE
# ==============================================================================

if st.button("🚀 RODAR BATERIA DE TESTES", type="primary"):
    df_res = executar_testes()
    
    # Métricas
    total = len(df_res)
    sucessos = len(df_res[df_res['Status'].str.contains("SUCESSO") | df_res['Status'].str.contains("OK")])
    falhas = total - sucessos
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Total de Casos", total)
    k2.metric("Sucessos", sucessos)
    k3.metric("Falhas", falhas, delta_color="inverse")
    
    # Tabela Colorida
    st.dataframe(
        df_res.style.applymap(lambda x: 'background-color: #d4edda; color: green' if 'SUCESSO' in str(x) else ('background-color: #f8d7da; color: red' if 'FALHA' in str(x) else ''), subset=['Status']),
        use_container_width=True,
        height=500
    )
    
    if falhas == 0:
        st.success("🏆 PARABÉNS! O Parser passou em todos os casos de regressão!")
    else:
        st.error("🚨 ATENÇÃO: Há regressões. Não atualize o sistema ainda.")

st.markdown("---")
st.info("ℹ️ Use esta página sempre que alterar o `parser_notam.py`. O objetivo é manter todas as linhas VERDES.")