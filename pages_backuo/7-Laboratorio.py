import streamlit as st
import pandas as pd
import time
from utils import ui

# Importações do seu projeto
from utils import db_manager
# Assumindo que sua função de parse está em utils.parser_notam
# Se estiver em outro lugar, ajuste o import:
from utils.parser_notam import interpretar_periodo_atividade 
from utils.casos_reais import CASOS_BLINDADOS

st.set_page_config(page_title="Laboratório de Regressão", layout="wide", page_icon="🧪")
ui.setup_sidebar() # <--- Chama o logo aqui

st.title("🧪 Laboratório & Diagnóstico")
st.markdown("Ferramenta de validação de integridade do parser e auditoria de dados do Supabase.")

tab_regressao, tab_auditoria = st.tabs(["🤖 Regressão Automática (Testes)", "📡 Auditoria Supabase (Reais)"])

# ==============================================================================
# TAB 1: REGRESSÃO AUTOMÁTICA (Os Casos de Teste)
# ==============================================================================
with tab_regressao:
    st.write("Verifica se a lógica do parser continua respeitando os gabaritos dos casos conhecidos.")
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    
    if st.button("▶️ Rodar Bateria de Testes", type="primary"):
        resultados = []
        passou = 0
        falhou = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_casos = len(CASOS_BLINDADOS)
        
        for i, caso in enumerate(CASOS_BLINDADOS):
            status_text.text(f"Testando: {caso['id']}...")
            
            # 1. Executa o Parser
            try:
                slots = interpretar_periodo_atividade(
                    item_d_text=caso['d'],
                    icao="TESTE",
                    item_b_raw=caso['b'],
                    item_c_raw=caso['c']
                )
                qtd_obtida = len(slots)
                qtd_esperada = caso['esperado']['qtd_slots']
                
                # 2. Valida
                if qtd_obtida == qtd_esperada:
                    status = "✅ Sucesso"
                    passou += 1
                    obs = "OK"
                else:
                    status = "❌ Falha"
                    falhou += 1
                    obs = f"Esperado: {qtd_esperada} | Obtido: {qtd_obtida}"
                    
            except Exception as e:
                status = "⚠️ Erro"
                falhou += 1
                obs = f"Exception: {str(e)}"
            
            resultados.append({
                "ID": caso['id'],
                "Descrição": caso['desc'],
                "Status": status,
                "Obs": obs,
                "Texto D": caso['d']
            })
            
            # Atualiza barra
            progress_bar.progress((i + 1) / total_casos)
            time.sleep(0.01) # Pequeno delay visual

        progress_bar.empty()
        status_text.empty()

        # --- Exibe KPIs ---
        col_kpi1.metric("Total de Casos", total_casos)
        col_kpi2.metric("Sucessos", passou)
        col_kpi3.metric("Falhas", falhou, delta_color="inverse")

        # --- Exibe Tabela ---
        df_res = pd.DataFrame(resultados)
        
        st.dataframe(
            df_res,
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn("Resultado"),
            },
            hide_index=True
        )

        if falhou == 0:
            st.success("🏆 Todos os sistemas operacionais! O Parser V18.5 está íntegro.")
        else:
            st.error("🚨 Atenção: Regressão detectou falhas na lógica.")

# ==============================================================================
# TAB 2: AUDITORIA SUPABASE (Dados Reais)
# ==============================================================================
with tab_auditoria:
    st.write("Analisa NOTAMs reais gravados no banco que possuem o campo 'D' preenchido.")
    
    if st.button("🔍 Auditar Banco de Dados"):
        with st.status("Lendo dados do Supabase...", expanded=True) as status:
            # 1. Carregar dados
            df_full = db_manager.carregar_notams()
            
            # 2. Filtrar apenas os que tem campo D
            if 'd' in df_full.columns:
                df_audit = df_full[df_full['d'].notna() & (df_full['d'] != '')].copy()
            else:
                st.error("Coluna 'd' não encontrada no banco.")
                st.stop()
            
            status.write(f"Encontrados {len(df_audit)} NOTAMs com campo 'D'. Iniciando análise...")
            
            report = []
            
            # 3. Iterar e verificar
            for idx, row in df_audit.iterrows():
                notam_id = row.get('id', 'N/A')
                d_text = row['d']
                b_raw = row['b']
                c_raw = row['c']
                icao = row['loc']
                
                diag_status = "OK"
                detalhe = ""
                qtd_slots = 0
                
                try:
                    # Roda o parser nos dados reais
                    slots = interpretar_periodo_atividade(d_text, icao, b_raw, c_raw)
                    qtd_slots = len(slots)
                    
                    if qtd_slots == 0:
                        diag_status = "⚠️ Zero Slots"
                        detalhe = "Parser não gerou nenhum horário."
                    
                except Exception as e:
                    diag_status = "❌ Erro Crítico"
                    detalhe = str(e)
                
                # Adiciona ao relatório se não for OK ou se quiser listar tudo
                if diag_status != "OK": # Focamos apenas nos problemas
                    report.append({
                        "ID": notam_id,
                        "ICAO": icao,
                        "Status": diag_status,
                        "Slots": qtd_slots,
                        "Detalhe": detalhe,
                        "Texto D": d_text,
                        "Início (B)": b_raw,
                        "Fim (C)": c_raw
                    })
            
            status.update(label="Auditoria concluída!", state="complete", expanded=False)
            
            # 4. Exibição
            if report:
                df_report = pd.DataFrame(report)
                st.warning(f"Foram encontradas **{len(df_report)}** anomalias em {len(df_audit)} registros analisados.")
                
                st.dataframe(
                    df_report,
                    use_container_width=True,
                    column_config={
                        "ID": st.column_config.TextColumn("ID Notam"),
                        "Status": st.column_config.TextColumn("Diagnóstico"),
                    },
                    hide_index=True
                )
            else:
                st.success(f"🎉 Incrível! Todos os {len(df_audit)} NOTAMs complexos foram processados com sucesso (geraram > 0 slots).")