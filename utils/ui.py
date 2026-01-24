import streamlit as st
import base64
import os

# ... (mantém as funções setup_sidebar e get_base64_bin)

def barra_superior():
    """Injeta a barra laranja e ajusta o tamanho do texto/ícones do menu lateral."""
    nome_usuario = st.session_state.get('usuario_atual', 'Usuário')
    logo_base64 = get_base64_bin("assets/logo-voegol-new.svg")
    img_src = f"data:image/svg+xml;base64,{logo_base64}" if logo_base64 else ""

    st.markdown(f"""
        <div class="custom-navbar">
            <div class="nav-left">
                <img src="{img_src}" class="nav-logo">
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
            /* Barra Superior Laranja */
            .custom-navbar {{
                position: fixed;
                top: 0; left: 0; width: 100%; height: 60px;
                background-color: #FF7020;
                z-index: 9999999;
                display: flex; align-items: center; justify-content: space-between;
                padding: 0 20px; color: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                font-family: sans-serif;
            }}
            
            .nav-logo {{ height: 35px; margin-right: 15px; filter: brightness(0) invert(1); }}

            /* --- NOVO: AJUSTE DO MENU LATERAL --- */
            
            /* Aumenta o texto dos links de navegação */
            [data-testid="stSidebarNav"] span {{
                font-size: 1.15rem !important; /* Ajuste este valor para o tamanho do texto */
                font-weight: 500 !important;
            }}

            /* Aumenta os ícones do Material Symbols no menu */
            [data-testid="stSidebarNav"] span[data-testid="stIconMaterial"] {{
                font-size: 1.5rem !important; /* Ajuste este valor para o tamanho do ícone */
            }}
            
            /* Aumenta o espaçamento entre os itens para não ficarem amontoados */
            [data-testid="stSidebarNav"] li {{
                margin-bottom: 5px !important;
            }}

            /* --- FIM DO AJUSTE --- */

            [data-testid="stSidebar"] {{ padding-top: 60px !important; }}
            .main .block-container {{ padding-top: 90px !important; }}
            header {{ visibility: hidden; }}
            [data-testid="stHeader"] {{ top: 60px !important; background-color: transparent !important; }}
        </style>
    """, unsafe_allow_html=True)