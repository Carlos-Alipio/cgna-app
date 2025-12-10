import streamlit as st
import pandas as pd
from utils import db_manager, formatters

st.set_page_config(page_title="Alertas Críticos", layout="wide")
st.title("🚨 Monitoramento Crítico")

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

st.divider()

# 1. CARREGAR DADOS
df_notams = db_manager.carregar_notams()
df_config = db_manager.carregar_filtros_configurados()

# 2. CARREGAR REGRAS DE FILTRO
filtros_assunto = df_config[df_config['tipo'] == 'assunto']['valor'].tolist()
filtros_condicao = df_config[df_config['tipo'] == 'condicao']['valor'].tolist()

# Validação se existe configuração
if not filtros_assunto or not filtros_condicao:
    st.warning("⚠️ Você ainda não configurou os filtros críticos.")
    st.info("Vá em **Configurações > Filtros Críticos** e selecione os assuntos (ex: Pista) e condições (ex: Fechado) que deseja monitorar aqui.")
    st.stop()

# 3. APLICAR FILTRO
if not df_notams.empty:
    
    # Filtra por FROTA (opcional, mas recomendado para não ver coisa irrelevante)
    frota = db_manager.carregar_frota_monitorada()
    if frota:
        df_base = df_notams[df_notams['loc'].isin(frota)]
    else:
        df_base = df_notams

    # --- O FILTRO DE OURO ---
    # Mostra apenas se o Assunto ESTÁ na lista E a Condição TAMBÉM ESTÁ na lista
    mask_assunto = df_base['assunto_desc'].isin(filtros_assunto)
    mask_condicao = df_base['condicao_desc'].isin(filtros_condicao)
    
    df_critico = df_base[mask_assunto & mask_condicao].copy()
    
    # 4. EXIBIÇÃO
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"### 🎯 Ocorrências Encontradas: {len(df_critico)}")
    
    # Mostra as regras ativas
    with c2.expander("Ver Regras Ativas"):
        st.write("**Assuntos:**", filtros_assunto)
        st.write("**Condições:**", filtros_condicao)

    if not df_critico.empty:
        # Ordena por data
        if 'dt' in df_critico.columns:
            df_critico = df_critico.sort_values(by='dt', ascending=False)
            df_critico['dt_visual'] = df_critico['dt'].apply(formatters.formatar_data_notam)

        # Seleciona colunas
        cols = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'dt_visual', 'e']
        
        # Estilização para dar ênfase (Vermelho claro se for crítico)
        st.dataframe(
            df_critico[cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "loc": "Local",
                "n": "Número",
                "assunto_desc": "Assunto",
                "condicao_desc": "Condição",
                "dt_visual": "Data",
                "e": "Texto Completo"
            }
        )
        
        # Botão para download rápido (útil para reportar)
        csv = df_critico[cols].to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Relatório Crítico (CSV)", data=csv, file_name="notams_criticos.csv", mime="text/csv")

    else:
        st.success("✅ Nenhuma ocorrência crítica encontrada com os filtros atuais.")
        st.balloons() # Um toque visual para indicar que "está tudo bem"

else:
    st.info("Banco de dados vazio. Atualize a base na página principal.")