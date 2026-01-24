import streamlit as st
import base64
import os

def setup_sidebar():
    """Menu lateral limpo."""
    pass

def get_base64_bin(file_path):
    """Converte arquivo local para base64 para o HTML."""
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
    except Exception:
        return ""
    return ""

def barra_superior():
    """Barra laranja #FF7020 com Relógio UTC e correção de visibilidade do menu."""
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
            /* 1. Barra Superior Laranja */
            .custom-navbar {{
                position: fixed;
                top: 0; left: 0; width: 100%; height: 60px;
                background-color: #FF7020;
                z-index: 999999;
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

            /* 2. CORREÇÃO DA SIDEBAR (BOTÃO E MENU) */
            
            /* Torna o botão do menu (hambúrguer) visível e branco sobre o laranja */
            [data-testid="stHeader"] {{
                background-color: transparent !important;
                z-index: 1000000 !important;
                color: white !important;
            }}
            
            /* Altera a cor do ícone do botão para branco */
            [data-testid="stHeader"] svg {{
                fill: white !important;
            }}

            /* Espaçamento do menu para não sumir sob a barra */
            [data-testid="stSidebar"] {{
                padding-top: 60px !important;
            }}

            /* Ajuste de itens do menu */
            [data-testid="stSidebarNav"] span {{ font-size: 1.0rem !important; }}
            [data-testid="stSidebarNav"] span[data-testid="stIconMaterial"] {{ font-size: 1.25rem !important; }}
            [data-testid="stSidebarNav"] li {{ margin-bottom: 6px !important; }}

            /* 3. BOTÃO SAIR NO RODAPÉ */
            [data-testid="stSidebarContent"] {{
                display: flex;
                flex-direction: column;
            }}
            
            [data-testid="stSidebarNav"] {{
                flex: 1;
            }}

            /* Posicionamento do último bloco (botão Sair) */
            div.stSidebar [data-testid="stVerticalBlock"] > div:last-child {{
                margin-top: auto;
                padding-bottom: 20px;
                display: flex;
                justify-content: center;
            }}

            /* 4. Ajuste Geral do Conteúdo */
            .main .block-container {{ padding-top: 80px !important; }}
            
            /* REMOVIDO: header {{ visibility: hidden; }} - Isso era o que matava o menu */
        </style>
    """, unsafe_allow_html=True)