import streamlit as st
import base64
import os

def setup_sidebar():
    """Menu lateral limpo."""
    pass

def get_base64_bin(file_path):
    """Converte o logo local para base64 para o HTML."""
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
    except Exception:
        return ""
    return ""

def barra_superior():
    """Injeta a barra laranja e o botão de menu exatamente onde foi solicitado (X vermelho)."""
    nome_usuario = st.session_state.get('usuario_atual', 'Usuário')
    logo_b64 = get_base64_bin("assets/logo-voegol-new.svg")
    img_src = f"data:image/svg+xml;base64,{logo_b64}" if logo_b64 else ""

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
            /* 1. BARRA SUPERIOR LARANJA #FF7020 */
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
            .nav-logo {{ height: 30px; margin-right: 15px; filter: brightness(0) invert(1); }}
            .nav-brand {{ font-weight: 800; font-size: 1.0rem; border-left: 1px solid rgba(255,255,255,0.3); padding-left: 15px; }}
            .nav-user {{ margin-left: 15px; font-weight: 300; font-size: 0.8rem; opacity: 0.9; }}
            .clock {{ font-size: 1.1rem; font-weight: 700; }}
            .clock-label {{ font-size: 0.55rem; opacity: 0.8; letter-spacing: 0.5px; }}

            /* 2. O BOTÃO DO MENU (POSIÇÃO DO X VERMELHO) */
            [data-testid="stHeader"] {{
                position: fixed !important;
                top: 70px !important; /* Logo abaixo da barra de 60px */
                left: 15px !important; /* No canto esquerdo conforme o seu X */
                width: 45px !important;
                height: 45px !important;
                background-color: white !important; /* Fundo branco para destaque */
                border-radius: 50% !important; /* Formato circular profissional */
                box-shadow: 0 2px 10px rgba(0,0,0,0.15) !important;
                z-index: 10000000 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }}
            
            /* Ajusta a cor do ícone da seta/hambúrguer para cinza escuro */
            [data-testid="stHeader"] svg {{
                fill: #444 !important;
                width: 24px !important;
                height: 24px !important;
            }}

            /* Esconde os botões inúteis (Share, Star) que poluem a barra laranja */
            [data-testid="stHeader"] > div:last-child {{
                display: none !important;
            }}

            /* 3. MENU LATERAL E CONTEÚDO */
            [data-testid="stSidebar"] {{ padding-top: 60px !important; }}
            [data-testid="stSidebarNav"] span {{ font-size: 1.0rem !important; }}
            [data-testid="stSidebarNav"] li {{ margin-bottom: 6px !important; }}

            /* Botão Sair no Rodapé */
            [data-testid="stSidebarContent"] {{ display: flex; flex-direction: column; height: 100vh; }}
            [data-testid="stSidebarNav"] {{ flex-grow: 1; }}
            div.stSidebar [data-testid="stVerticalBlock"] > div:last-child {{
                margin-top: auto; padding: 20px 10px; display: flex; justify-content: center;
                border-top: 1px solid rgba(0,0,0,0.05);
            }}
            div.stSidebar [data-testid="stVerticalBlock"] > div:last-child button {{ width: 85% !important; }}

            /* Padding do conteúdo principal */
            .main .block-container {{ padding-top: 110px !important; }}
        </style>
    """, unsafe_allow_html=True)