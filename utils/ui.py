import streamlit as st
import base64
import os

def setup_sidebar():
    """Menu lateral limpo."""
    pass

def get_base64_bin(file_path):
    """Converte arquivo local para base64 para uso em HTML."""
    try:
        # Removida a barra inicial para garantir que o caminho funcione no Cloud
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
    except Exception:
        return ""
    return ""

def barra_superior():
    """Barra laranja #FF7020 com Relógio UTC funcional e CSS de ajuste."""
    nome_usuario = st.session_state.get('usuario_atual', 'Usuário')
    logo_b64 = get_base64_bin("assets/logo-voegol-new.svg")
    img_src = f"data:image/svg+xml;base64,{logo_b64}" if logo_b64 else ""

    st.markdown(f"""
        <div class="custom-navbar">
            <div class="nav-left">
                <img src="{img_src}" class="nav-logo">
                <span class="nav-brand">CGNA | </span>
                <span class="nav-user">{nome_usuario}</span>
            </div>
            <div class="nav-right">
                <div id="utc-clock" class="clock">--:--:-- UTC</div>
                <div class="clock-label">Tempo Universal Coordenado</div>
            </div>
        </div>

        <script>
            // Função encapsulada para evitar conflitos
            (function() {{
                function updateClock() {{
                    const now = new Date();
                    const h = String(now.getUTCHours()).padStart(2, '0');
                    const m = String(now.getUTCMinutes()).padStart(2, '0');
                    const s = String(now.getUTCSeconds()).padStart(2, '0');
                    const clockEl = document.getElementById('utc-clock');
                    if (clockEl) {{
                        clockEl.innerText = h + ":" + m + ":" + s + " UTC";
                    }}
                }}
                
                // Limpa intervalo anterior se existir para não sobrecarregar
                if (window.utcInterval) clearInterval(window.utcInterval);
                
                // Inicia o relógio
                window.utcInterval = setInterval(updateClock, 1000);
                updateClock();
            }})();
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
            
            .nav-logo {{ height: 35px; margin-right: 15px; filter: brightness(0) invert(1); }}
            .nav-brand {{ font-weight: 800; font-size: 1.1rem; border-left: 1px solid rgba(255,255,255,0.3); padding-left: 15px; }}
            .nav-user {{ margin-left: 10px; font-weight: 300; font-size: 0.9rem; opacity: 0.9; }}
            
            .nav-right {{ text-align: right; line-height: 1.1; min-width: 150px; }}
            .clock {{ font-size: 1.2rem; font-weight: 700; font-variant-numeric: tabular-nums; }}
            .clock-label {{ font-size: 0.6rem; opacity: 0.8; letter-spacing: 0.5px; }}

            /* 2. Ajustes de Navegação e Sidebar */
            [data-testid="stSidebar"] {{ padding-top: 60px !important; }}
            [data-testid="stHeader"] {{ top: 60px !important; background-color: transparent !important; z-index: 1000000 !important; }}
            
            /* Ajuste de itens do menu */
            [data-testid="stSidebarNav"] span {{ font-size: 1.15rem !important; }}
            [data-testid="stSidebarNav"] span[data-testid="stIconMaterial"] {{ font-size: 1.5rem !important; }}
            [data-testid="stSidebarNav"] li {{ margin-bottom: 12px !important; }}

            /* 3. Ajuste do Conteúdo Principal */
            .main .block-container {{ padding-top: 100px !important; }}
            
            /* Esconde ícones nativos desnecessários */
            [data-testid="stHeader"] > div:last-child {{ display: none !important; }}
        </style>
    """, unsafe_allow_html=True)