import streamlit as st

def setup_sidebar():
    """Configura o logo no menu lateral."""
    st.logo("assets/logo-voegol-new.svg")

def barra_superior():
    """Injeta a barra azul com Relógio UTC e ajusta o posicionamento do menu lateral."""
    nome_usuario = st.session_state.get('usuario_atual', 'Usuário')
    
    st.markdown(f"""
        <div class="custom-navbar">
            <div class="nav-left">
                <span class="nav-brand">✈️ CGNA | GOL</span>
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
            /* 1. Barra Superior Fixa */
            .custom-navbar {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 60px;
                background-color: #0d6efd;
                z-index: 9999999; /* Z-index altíssimo para ficar sobre tudo */
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 20px;
                color: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                font-family: sans-serif;
            }}
            
            /* 2. RESOLUÇÃO: Empurra o Menu Lateral para baixo */
            [data-testid="stSidebar"] {{
                padding-top: 60px !important;
            }}

            /* 3. Empurra o Conteúdo Principal para baixo */
            .main .block-container {{
                padding-top: 85px !important;
            }}

            /* Estética dos itens da barra */
            .nav-left {{ display: flex; align-items: center; }}
            .nav-brand {{ font-weight: 800; font-size: 1.1rem; }}
            .nav-user {{ margin-left: 20px; font-weight: 300; font-size: 0.85rem; border-left: 1px solid rgba(255,255,255,0.3); padding-left: 20px; }}
            .clock {{ font-size: 1.2rem; font-weight: 700; }}
            .clock-label {{ font-size: 0.6rem; opacity: 0.8; letter-spacing: 1px; }}

            /* Esconde cabeçalhos originais do Streamlit */
            header {{ visibility: hidden; }}
            [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
        </style>
    """, unsafe_allow_html=True)