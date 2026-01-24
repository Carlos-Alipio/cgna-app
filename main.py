import streamlit as st
from utils import ui, db_manager

# 1. Configuração da Página (Sempre o primeiro comando!)
st.set_page_config(
    page_title="Gerenciador CGNA", 
    page_icon=":material/flight_takeoff:", 
    layout="wide"
)

# 2. Configura o Sidebar (Logo e estilo Bootstrap)
ui.setup_sidebar()

# 3. Definição das Páginas
# O ícone usa os Material Symbols que você queria!
pg_inicio = st.Page(
    "pages/inicio.py", 
    title="Home", 
    icon=":material/home:", 
    default=True
)

pg_obras = st.Page(
    "pages/4-Monitoramento_Obras.py", 
    title="Monitoramento Obras", 
    icon=":material/construction:"
)

pg_notam = st.Page(
    "pages/notam_view.py", # Exemplo de outra página
    title="Notam", 
    icon=":material/description:"
)

# 4. Criação e Execução da Navegação
pg = st.navigation({
    "Principal": [pg_inicio],
    "Operacional": [pg_obras, pg_notam]
})

pg.run()


#pg_home = st.Page("pages/Home.py", title="Visão Geral", icon=":material/home:")
#pg_notam = st.Page("pages/Notam.py", title="Notam", icon=":material/connecting_airports:")
#pg_obras = st.Page("pages/Monitoramento_Obras.py", title="Gestão de Obras", icon=":material/construction:")
#pg_config = st.Page("pages/Configuracoes.py", title="Ajustes", icon=":material/settings:")
