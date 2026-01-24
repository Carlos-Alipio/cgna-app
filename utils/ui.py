import streamlit as st

def setup_sidebar():
    """Menu lateral limpo, sem o logo que foi para a barra superior."""
    # st.logo foi removido daqui para evitar duplicidade
    pass

def barra_superior():
    """Barra horizontal laranja com Logo, Nome e Relógio UTC."""
    nome_usuario = st.session_state.get('usuario_atual', 'Usuário')
    
    st.markdown(f"""
        <div class="custom-navbar">
            <div class="nav-left">
                <img src="https://www.voegol.com.br/assets/img/logo-gol.png" class="nav-logo">
                <span class="nav-brand">CGNA | GOL</span>
                <span class="nav-user">👤 {nome_usuario}</span>
            </div>
            <div class="nav-right">
                <div id="utc-clock" class="clock">00:00:00 UTC</div>
                <div class="clock-label">Tempo Universal Coordenado</div>
            </div>
        </div>

        <script>
            function updateClock() {{
                const now = new Date();
                const h = String(now.getUTCHours()).padStart(2, '0');
                const m = String(now.getUTCMinutes()).padStart(2, '0');
                const s = String(now.getUTCSeconds()).padStart(2, '0');
                const clockEl = document.getElementById('utc-clock');
                if (clockEl) clockEl.innerText = h + ":" + m + ":" + s + " UTC";
            }}
            if (window.utcInterval) clearInterval(window.utcInterval);
            window.utcInterval = setInterval(updateClock, 1000);
            updateClock();
        </script>

        <style>
            /* 1. Barra Superior com a nova cor #FF7020 */
            .custom-navbar {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 60px;
                background-color: #FF7020; /* Cor Laranja solicitada */
                z-index: 9999999;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 20px;
                color: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                font-family: sans-serif;
            }}
            
            /* Estilo do Logo na Barra */
            .nav-logo {{
                height: 30px;
                margin-right: 15px;
                filter: brightness(0) invert(1); /* Deixa o logo branco para contrastar com o laranja */
            }}

            .nav-left {{ display: flex; align-items: center; }}
            .nav-brand {{ font-weight: 800; font-size: 1.1rem; border-left: 1px solid rgba(255,255,255,0.3); padding-left: 15px; }}
            .nav-user {{ margin-left: 15px; font-weight: 300; font-size: 0.85rem; opacity: 0.9; }}
            
            .nav-right {{ text-align: right; line-height: 1.1; }}
            .clock {{ font-size: 1.2rem; font-weight: 700; }}
            .clock-label {{ font-size: 0.6rem; opacity: 0.8; letter-spacing: 0.5px; }}

            /* Ajustes de Layout Streamlit */
            [data-testid="stSidebar"] {{ padding-top: 60px !important; }}
            .main .block-container {{ padding-top: 90px !important; }}
            header {{ visibility: hidden; }}
            [data-testid="stHeader"] {{ top: 60px !important; background-color: transparent !important; }}
        </style>
    """, unsafe_allow_html=True)