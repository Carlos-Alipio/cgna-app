import streamlit as st

# Configuração da página DEVE ser a primeira coisa no script principal
st.set_page_config(page_title="Gerenciador CGNA", page_icon=":material/flight_takeoff:", layout="wide")

# Importe seu utilitário de UI
from utils import ui
ui.setup_sidebar()

# 1. Defina as páginas apontando para os arquivos na pasta /pages
# DICA: Mova o conteúdo que estava no Home.py original para pages/inicio.py
pg_home = st.Page("pages/Home.py", title="Visão Geral", icon=":material/home:")
pg_notam = st.Page("pages/Notam.py", title="Notam", icon=":material/connecting_airports:")
pg_obras = st.Page("pages/Monitoramento_Obras.py", title="Gestão de Obras", icon=":material/construction:")
pg_config = st.Page("pages/Configuracoes.py", title="Ajustes", icon=":material/settings:")

# 2. Crie a navegação
pg = st.navigation([pg_home, pg_notam, pg_obras, pg_config])

# 3. Execute a navegação
pg.run()