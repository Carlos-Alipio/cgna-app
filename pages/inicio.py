import streamlit as st
from utils import ui
from utils import db_manager

def main():
    ui.barra_superior()
    
    nome_usuario = st.session_state.get('usuario_atual', 'Carlos Alípio')
    stats = db_manager.buscar_estatisticas_dashboard()

    st.title(f"Bem-vindo, {nome_usuario}")
    st.info("Acesso autorizado ao painel operacional.")

    st.divider()
    st.subheader("📊 Resumo Operacional")
    
    col1, col2 = st.columns(2)

    with col1:
        # Alterado de 'Obras' para 'Aeroportos Monitorados'
        st.metric(
            label="Aeroportos Monitorados", 
            value=stats["aeroportos"],
            help="Quantidade de localidades únicas com NOTAMs registrados."
        )

    with col2:
        # Total de NOTAMs na base de dados
        st.metric(
            label="Total de NOTAMs", 
            value=stats["total_notams"],
            help="Volume total de NOTAMs carregados no sistema."
        )


    st.divider()
    
    # Dica visual: O gráfico agora pode mostrar a proporção de NOTAMs por Aeroporto
    st.subheader("📈 Distribuição por Localidade")
    df = db_manager.carregar_notams()
    if not df.empty:
        # Agrupa por aeroporto para o gráfico
        chart_data = df['icaoairport_id'].value_counts()
        st.bar_chart(chart_data, color="#FF7020")

    st.caption("ℹ️ Utilize o menu 'Gestão de Obras' para detalhar os itens monitorados.")

if __name__ == "__main__":
    main()