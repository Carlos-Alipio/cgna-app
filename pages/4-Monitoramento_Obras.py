import streamlit as st
import pandas as pd
from utils import db_manager, formatters

st.set_page_config(page_title="Monitoramento Obras", layout="wide")
st.title("🚨 Monitoramento Obras")

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

st.divider()

# ==============================================================================
# 1. CARREGAR DADOS E REGRAS
# ==============================================================================
df_notams = db_manager.carregar_notams()
df_config = db_manager.carregar_filtros_configurados()

filtros_assunto = df_config[df_config['tipo'] == 'assunto']['valor'].tolist()
filtros_condicao = df_config[df_config['tipo'] == 'condicao']['valor'].tolist()

if not filtros_assunto or not filtros_condicao:
    st.warning("⚠️ Você ainda não configurou os filtros críticos.")
    st.info("Vá em **Configurações > Filtros Críticos** e selecione os assuntos e condições.")
    st.stop()

# ==============================================================================
# 2. APLICAR FILTRO LÓGICO
# ==============================================================================
if not df_notams.empty:
    
    frota = db_manager.carregar_frota_monitorada()
    if frota:
        df_base = df_notams[df_notams['loc'].isin(frota)]
    else:
        df_base = df_notams

    # Filtro: Assunto E Condição devem estar na lista configurada
    mask_assunto = df_base['assunto_desc'].isin(filtros_assunto)
    mask_condicao = df_base['condicao_desc'].isin(filtros_condicao)
    
    df_critico = df_base[mask_assunto & mask_condicao].copy()
    
    # ==============================================================================
    # 3. EXIBIÇÃO
    # ==============================================================================
    
    c1, c2 = st.columns([3, 1])
    
    if not df_critico.empty:
        c1.error(f"### 🎯 {len(df_critico)} Ocorrências Encontradas")
    else:
        c1.success("### ✅ Nenhuma ocorrência crítica no momento.")

    with c2.expander("Ver Regras Ativas"):
        st.write("**Assuntos:**", filtros_assunto)
        st.write("**Condições:**", filtros_condicao)

    st.markdown("---")

    if not df_critico.empty:
        # Ordenação
        if 'dt' in df_critico.columns:
            df_critico = df_critico.sort_values(by='dt', ascending=False)
            
        # Formatação para visualização (Datas)
        df_critico['Início'] = df_critico['b'].apply(formatters.formatar_data_notam)
        df_critico['Fim'] = df_critico['c'].apply(formatters.formatar_data_notam)

        # Definição das colunas
        cols_view = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'Início', 'Fim', 'd', 'e']
        
        # --- LIMPEZA DE "NONE" / "NAN" (NOVO) ---
        # Substitui valores nulos reais por vazio
        df_exibicao = df_critico[cols_view].fillna("")
        
        # Substitui textos "nan" ou "None" que o Pandas às vezes gera ao converter para string
        for col in df_exibicao.columns:
            df_exibicao[col] = df_exibicao[col].astype(str).replace({'nan': '', 'None': '', 'NaT': ''})
        # ----------------------------------------

        st.dataframe(
            df_exibicao,
            use_container_width=True,
            hide_index=True,
            column_config={
                "loc": "Local",
                "n": "NOTAM",
                "assunto_desc": "Assunto",
                "condicao_desc": "Condição",
                "d": "Período/Horário",
                "e": "Texto Completo"
            }
        )
        
        csv = df_exibicao.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Relatório (CSV)",
            data=csv,
            file_name="notams_criticos_gol.csv",
            mime="text/csv",
            type="primary"
        )

    else:
        st.balloons() 
        st.info("Com base nos seus filtros, a operação está normal.")

else:
    st.info("Banco vazio. Vá para a página 'Painel de Notams' e atualize a base.")