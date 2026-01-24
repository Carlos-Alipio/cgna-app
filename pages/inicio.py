import streamlit as st
from utils import ui
from utils import db_manager

def main():
    # 1. Injeta a barra superior personalizada (Laranja #FF7020)
    ui.barra_superior()

    # 2. Recupera informações de contexto
    nome_usuario = st.session_state.get('usuario_atual', 'Carlos Alípio')
    
    # 3. Busca os dados reais do Supabase via db_manager
    stats = db_manager.buscar_estatisticas_dashboard()

    # --- CABEÇALHO ---
    st.title(f"👋 Bem-vindo, {nome_usuario}")
    st.info("Acesso autorizado ao painel operacional.")

    st.divider()

    # --- SEÇÃO DE MÉTRICAS (KPIs) ---
    st.subheader("📊 Visão Geral em Tempo Real")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Obras em Monitoramento", 
            value=stats["obras"], 
            help="Total de obras com status 'Ativo' no banco de dados."
        )

    with col2:
        # Exemplo de delta fixo (pode ser automatizado futuramente)
        st.metric(
            label="NOTAMs Ativos", 
            value=stats["notams"], 
            delta="-2", 
            help="Quantidade de NOTAMs vigentes capturados pelo sistema."
        )

    with col3:
        # O valor "4m" é mantido como exemplo até a função de tempo ser implementada
        st.metric(
            label="Tempo Médio de Cadastro", 
            value=stats["tempo_medio"], 
            delta="15s",
            delta_color="inverse", # Vermelho se aumentar, pois tempo maior é pior
            help="Média de tempo entre a abertura e fechamento dos processos."
        )

    st.divider()

    # --- SEÇÃO DE GRÁFICO ---
    st.subheader("📈 Tendência de Atividade (NOTAMs)")
    
    # Exemplo de dados para o gráfico usando a cor da GOL
    chart_data = {
        "Dias": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"],
        "Processados": [12, 18, 15, 25, 22, 10, 14]
    }
    st.line_chart(chart_data, x="Dias", y="Processados", color="#FF7020")

    # --- RODAPÉ INFORMATIVO ---
    st.caption("ℹ️ Utilize o menu à esquerda para navegar entre as ferramentas de gestão e monitoramento.")

if __name__ == "__main__":
    main()