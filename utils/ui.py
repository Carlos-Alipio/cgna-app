import streamlit as st
import base64
import os

def setup_sidebar():
    """Menu lateral limpo."""
    pass

def get_base64_bin(file_path):
    """Converte arquivo local para base64 para uso em HTML."""
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
    except Exception:
        return ""
    return ""

def barra_superior():
    """Barra laranja #FF7020 com correção da posição da seta de colapso."""
    nome_usuario = st.session_state.get('usuario_atual', 'Usuário')
    
    # Processamento do Logo GOL
    logo_path = "assets/logo-voegol-new.svg"
    logo_b64 = get_base64_bin(logo_path)
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

            /* 2. RESOLUÇÃO DA SETA (CHEVRON) SOBRE O LOGO */
            /* Movemos o cabeçalho (onde fica a seta) para a direita do texto da marca */
            [data-testid="stHeader"] {{
                background-color: transparent !important;
                left: 220px !important; /* Move a seta para a direita do 'CGNA | GOL' */
                top: 0px !important;
                z-index: 10000000 !important; /* Garante que fique clicável sobre a barra */
                width: fit-content !important;
            }}
            
            /* Deixa a seta branca para combinar com a barra */
            [data-testid="stHeader"] svg {{
                fill: white !important;
            }}

            /* 3. Customização do Menu Lateral */
            [data-testid="stSidebar"] {{ padding-top: 60px !important; }}
            
            [data-testid="stSidebarNav"] span {{
                font-size: 1.0rem !important;
                font-weight: 400 !important;
            }}
            
            [data-testid="stSidebarNav"] span[data-testid="stIconMaterial"] {{
                font-size: 1.25rem !important;
            }}

            /* Espaçamento de 12px entre itens */
            [data-testid="stSidebarNav"] li {{
                margin-bottom: 12px !important;
            }}

            /* 4. BOTÃO SAIR NO RODAPÉ CENTRALIZADO */
            [data-testid="stSidebarContent"] {{
                display: flex;
                flex-direction: column;
                height: 100vh;
            }}

            [data-testid="stSidebarNav"] {{
                flex-grow: 1;
            }}

            div.stSidebar [data-testid="stVerticalBlock"] > div:last-child {{
                margin-top: auto;
                padding: 20px 10px;
                display: flex;
                justify-content: center;
                border-top: 1px solid rgba(0,0,0,0.05);
            }}
            
            div.stSidebar [data-testid="stVerticalBlock"] > div:last-child button {{
                width: 85% !important;
            }}

            /* 5. Ajustes de Tela */
            .main .block-container {{ padding-top: 100px !important; }}
            header {{ visibility: visible !important; }} /* Garante visibilidade da seta */
        </style>
    """, unsafe_allow_html=True)