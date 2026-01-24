import streamlit as st
from utils import ui
from utils import db_manager # Importa o gerenciador de banco

def main():
    nome_usuario = st.session_state.get('usuario_atual', 'Carlos Alípio')
    st.title(f"👋 Bem-vindo, {nome_usuario}")
    st.info("Acesso autorizado ao painel operacional.")

    # Busca os dados reais do banco
    stats = db_manager.buscar_estatisticas_dashboard()

    st.divider()
    st.subheader("📊 Visão Geral em Tempo Real")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Obras em Monitoramento", 
            value=stats["obras"], 
            help="Total de obras com status 'Ativo' no banco de dados."
        )

    with col2:
        # Exemplo de como você pode calcular o delta no futuro
        st.metric(
            label="NOTAMs Ativos", 
            value=stats["notams"], 
            delta="-2", # Você pode automatizar isso comparando com ontem
            help="Quantidade de NOTAMs vigentes capturados pelo sistema."
        )

    with col3:
        st.metric(
            label="Tempo Médio de Cadastro", 
            value=stats["tempo_medio"], 
            help="Média de tempo entre a abertura e fechamento dos processos."
        )

    st.divider()
    # ... resto do código (gráficos, etc)

# Garante que a barra apareça mesmo na troca de página
ui.barra_superior()

nome = st.session_state.get('usuario_atual', 'Usuário')

st.title(f"Bem-vindo, {nome}")
st.success("Acesso autorizado ao painel operacional.")

st.divider()


