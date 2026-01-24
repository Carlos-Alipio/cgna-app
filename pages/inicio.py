import streamlit as st
from utils import ui
from utils import db_manager

def main():
    ui.barra_superior()
    
    nome_usuario = st.session_state.get('usuario_atual', 'Carlos Alípio')
    stats = db_manager.buscar_estatisticas_dashboard()

    st.title(f"👋 Bem-vindo, {nome_usuario}")
    st.info("Acesso autorizado ao painel operacional.")

    st.divider()
    st.subheader("📊 Resumo Operacional")
    
    # Usaremos duas colunas largas para dar destaque aos números totais
    col1, col2 = st.columns(2)

    with col1:
        # Substituído pelo total sem filtros conforme solicitado
        st.metric(
            label="NOTAMs Totais", 
            value=stats["total_geral"],
            help="Soma total de todos os NOTAMs registrados na base de dados, sem filtros."
        )

    with col2:
        st.metric(
            label="Aeroportos Monitorados", 
            value=stats["aeroportos"],
            help="Quantidade de localidades distintas (ICAOs) presentes no banco."
        )

    st.divider()
    
    # Visualização de distribuição para complementar o total
    st.subheader("📈 NOTAMs por Aeroporto")
    df = db_manager.carregar_notams()
    if not df.empty:
        # Mostra os 10 aeroportos com mais NOTAMs para não poluir a tela
        chart_data = df['icaoairport_id'].value_counts().head(10)
        st.bar_chart(chart_data, color="#FF7020")

if __name__ == "__main__":
    main()