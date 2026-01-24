import streamlit as st
from utils import ui
from utils import db_manager

def main():
    # Injeta a barra superior (Versão limpa, sem relógio)
    ui.barra_superior()
    
    nome_usuario = st.session_state.get('usuario_atual', 'Carlos Alípio Flores de Morais')
    stats = db_manager.buscar_estatisticas_dashboard()

    # Cabeçalho de Boas-vindas
    st.title(f"👋 Bem-vindo, {nome_usuario}")
    st.info("Acesso autorizado ao painel operacional.")

    st.divider()
    
    # --- RESUMO OPERACIONAL ---
    # Ícone e título conforme a versão anterior
    st.markdown("### 📊 Resumo Operacional")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Aeroportos Monitorados", 
            value=stats["aeroportos"],
            help="Total de localidades únicas registradas"
        )

    with col2:
        st.metric(
            label="Total de NOTAMs", 
            value=stats["total_geral"],
            help="Volume total de NOTAMs na base"
        )

    with col3:
        # Valor que corresponde à tabela da imagem 'image_f92c9c.png'
        st.metric(
            label="NOTAMs em Gestão", 
            value=stats["em_gestao"],
            help="Quantidade de NOTAMs presentes na tela de Cadastro de Obras"
        )

    st.divider()
    
    # Mensagem de orientação no rodapé
    st.caption("Utilize o menu à esquerda para gerenciar os agendamentos das obras.")

if __name__ == "__main__":
    main()