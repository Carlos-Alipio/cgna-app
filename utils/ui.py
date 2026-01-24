import streamlit as st

def setup_sidebar():
    """Configura o logo no menu lateral."""
    st.logo("assets/logo-voegol-new.svg")

def barra_superior():
    """Insere a barra horizontal com Relógio UTC em tempo real e Nome do Usuário."""
    nome_usuario = st.session_state.get('usuario_atual', 'Usuário')
    
    st.markdown(f"""
        <div style='
            position: fixed; 
            top: 0; 
            left: 0; 
            width: 100%; 
            height: 60px; 
            background-color: #0d6efd; 
            z-index: 999999; 
            border-bottom: 3px solid #0a58ca; 
            display: flex; 
            align-items: center; 
            justify-content: space-between;
            padding: 0 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            color: white;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;'>
            
            <div style='display: flex; align-items: center;'>
                <span style='font-weight: 800; font-size: 1.2rem; letter-spacing: 1px;'>
                    ✈️ CGNA | GOL
                </span>
                <span style='margin-left: 20px; font-weight: 300; font-size: 0.9rem; opacity: 0.9; border-left: 1px solid rgba(255,255,255,0.3); padding-left: 20px;'>
                    👤 {nome_usuario}
                </span>
            </div>

            <div style='text-align: right;'>
                <div id="utc-clock" style='font-size: 1.3rem; font-weight: bold; font-variant-numeric: tabular-nums;'>
                    00:00:00 UTC
                </div>
                <div style='font-size: 0.7rem; opacity: 0.8; text-transform: uppercase;'>
                    Tempo Universal Coordenado
                </div>
            </div>
        </div>

        <script>
            function updateClock() {{
                const now = new Date();
                const h = String(now.getUTCHours()).padStart(2, '0');
                const m = String(now.getUTCMinutes()).padStart(2, '0');
                const s = String(now.getUTCSeconds()).padStart(2, '0');
                document.getElementById('utc-clock').innerText = h + ":" + m + ":" + s + " UTC";
            }}
            setInterval(updateClock, 1000);
            updateClock();
        </script>

        <style>
            .main .block-container {{
                padding-top: 85px !important;
            }}
            header {{visibility: hidden;}}
            [data-testid="stSidebarNav"] {{padding-top: 20px;}}
        </style>
    """, unsafe_allow_html=True)