import streamlit as st
import pandas as pd
from sqlalchemy import text
from utils import ui

# Importando módulos da pasta utils
from utils import db_manager
from utils.notam_codes import NOTAM_SUBJECT, NOTAM_CONDITION 

st.set_page_config(page_title="Configurações", layout="wide")
st.title("⚙️ Configurações do Sistema")
ui.setup_sidebar() # <--- Chama o logo aqui

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

# Cria abas para organizar as configurações
tab1, tab2 = st.tabs(["✈️ Frota (Aeroportos)", "🚨 Filtros Críticos"])

# ==============================================================================
# ABA 1: GERENCIAR FROTA (ICAO)
# ==============================================================================
with tab1:
    st.markdown("### 🛫 Aeroportos Monitorados")
    st.caption("Adicione os códigos ICAO (ex: SBGR) que o sistema deve baixar e monitorar.")
    
    # 1. Carrega lista atual
    df_frota = pd.DataFrame(db_manager.carregar_frota_monitorada(), columns=['icao'])
    
    if not df_frota.empty:
        # Mostra lista
        lista_atual = ", ".join(df_frota['icao'].tolist())
        st.info(f"**Atualmente Monitorando ({len(df_frota)}):** {lista_atual}")
        
        # Área de Remoção
        with st.expander("🗑️ Remover Aeroporto"):
            c_del1, c_del2 = st.columns([3, 1])
            to_delete = c_del1.selectbox("Selecione para remover:", df_frota['icao'])
            if c_del2.button("Remover ICAO"):
                if db_manager.remover_icao(to_delete):
                    st.success(f"{to_delete} removido!")
                    st.rerun()
                else:
                    st.error("Erro ao remover.")
    else:
        st.warning("Sua lista de monitoramento está vazia.")

    st.divider()

    # Área de Adição
    st.markdown("#### ➕ Adicionar Novos")
    c1, c2 = st.columns(2)
    
    # Adição Individual
    with c1.container(border=True):
        st.markdown("**Individual**")
        novo_icao = st.text_input("Código ICAO (4 letras)", placeholder="Ex: SBGL").upper().strip()
        desc_icao = st.text_input("Descrição (Opcional)", placeholder="Ex: Galeão")
        
        if st.button("Salvar Aeroporto"):
            if len(novo_icao) == 4:
                if db_manager.adicionar_icao(novo_icao, desc_icao):
                    st.success(f"{novo_icao} adicionado com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao salvar (talvez já exista).")
            else:
                st.warning("O código ICAO deve ter exatamente 4 letras.")

    # Adição em Lote
    with c2.container(border=True):
        st.markdown("**Carga em Lote**")
        texto_lote = st.text_area("Cole a lista (separada por vírgula)", placeholder="SBGR, SBSP, SBRJ, CONF", height=108)
        
        if st.button("Processar Lista"):
            if texto_lote:
                lista = [x.strip().upper() for x in texto_lote.split(',') if len(x.strip()) == 4]
                count = 0
                for i in lista:
                    if db_manager.adicionar_icao(i, "Carga em Lote"):
                        count += 1
                st.success(f"{count} aeroportos importados!")
                st.rerun()

# ==============================================================================
# ABA 2: FILTROS CRÍTICOS (PARA A PÁGINA DE ALERTAS)
# ==============================================================================
with tab2:
    st.markdown("### 🚨 Configuração de Alertas")
    st.caption("Defina aqui o que deve aparecer na página **'Monitoramento Crítico'**. O sistema cruzará Assunto + Condição.")

    # 1. Carrega configurações salvas no banco
    df_configs = db_manager.carregar_filtros_configurados()
    
    # Extrai listas salvas para preencher os multiselects
    if not df_configs.empty:
        assuntos_salvos = df_configs[df_configs['tipo'] == 'assunto']['valor'].tolist()
        condicoes_salvas = df_configs[df_configs['tipo'] == 'condicao']['valor'].tolist()
    else:
        assuntos_salvos = []
        condicoes_salvas = []

    # 2. Prepara opções (Dicionários completos)
    todas_opcoes_assunto = sorted(list(NOTAM_SUBJECT.values()))
    todas_opcoes_condicao = sorted(list(NOTAM_CONDITION.values()))

    # Formulário para salvar tudo de uma vez
    with st.form("form_filtros_criticos"):
        col_ass, col_cond = st.columns(2)
        
        with col_ass:
            st.subheader("📂 1. Assuntos Críticos")
            st.caption("O que você quer monitorar? (Ex: Pista, ILS)")
            novos_assuntos = st.multiselect(
                "Selecione os Assuntos:",
                options=todas_opcoes_assunto,
                default=[x for x in assuntos_salvos if x in todas_opcoes_assunto]
                # height=300  <-- REMOVIDO PARA CORRIGIR O ERRO
            )
            
        with col_cond:
            st.subheader("🔧 2. Condições Críticas")
            st.caption("Qual o estado grave? (Ex: Fechado, Inoperante)")
            novas_condicoes = st.multiselect(
                "Selecione as Condições:",
                options=todas_opcoes_condicao,
                default=[x for x in condicoes_salvas if x in todas_opcoes_condicao]
                # height=300 <-- REMOVIDO PARA CORRIGIR O ERRO
            )
            
        st.write("")
        st.markdown("---")
        
        # Botão de Salvar
        # Criamos colunas para centralizar ou alinhar o botão, se desejar
        c_submit = st.columns([1, 2, 1])[1]
        
        # Este botão DEVE estar dentro do 'with st.form'
        if c_submit.form_submit_button("💾 Salvar Definições de Alerta", type="primary", use_container_width=True):
            ok1 = db_manager.atualizar_filtros_lote('assunto', novos_assuntos)
            ok2 = db_manager.atualizar_filtros_lote('condicao', novas_condicoes)
            
            if ok1 and ok2:
                st.success("✅ Configurações de alerta atualizadas com sucesso!")
                st.rerun()
            else:
                st.error("Houve um erro ao salvar as configurações no banco.")