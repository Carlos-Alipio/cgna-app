import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from utils import ui

# Importando módulos da pasta utils
from utils import db_manager, api_decea, formatters

st.set_page_config(page_title="Monitoramento GOL", layout="wide")
st.title("Monitoramento de NOTAMs")
ui.setup_sidebar() # <--- Chama o logo aqui

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

# Inicializa lista de IDs novos na sessão (para o realce verde)
if 'novos_ids' not in st.session_state:
    st.session_state['novos_ids'] = []





import streamlit as st
# Certifique-se de que o módulo 'formatters' está importado no seu arquivo principal

# ==============================================================================
# FUNÇÃO DO POP-UP (MODAL) Exibe os detalhes do NOTAM em uma janela modal.
# ==============================================================================
@st.dialog("Detalhes do NOTAM", width="large")
def exibir_detalhes_popup(dados):

    # --- INÍCIO DA INJEÇÃO DE CSS ---
    st.markdown(
        """
        <style>
        /* 1. FAIXA LARANJA NO TÍTULO DO MODAL */
        div[role="dialog"] header {
            background-color: #FF8C00 !important; /* Cor Laranja (DarkOrange) */
            border-bottom: 2px solid #E67E22 !important; /* Borda leve para dar profundidade */
        }
        
        /* 2. TEXTO DO TÍTULO EM BRANCO E NEGRITO */
        div[role="dialog"] header h2 {
            color: white !important; 
            font-weight: 800 !important;
        }
        
        /* 3. BOTÃO DE FECHAR (X) EM BRANCO PARA DAR CONTRASTE */
        div[role="dialog"] header button svg {
            stroke: white !important;
            fill: white !important;
        }

        /* 4. AJUSTES DOS CAMPOS METRIC (Mantidos das versões anteriores) */
        [data-testid="stMetricValue"] {
            font-size: 1.4rem !important; 
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.9rem !important;
            margin-bottom: -4px !important; 
            color: #808080 !important; 
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    # --- FIM DA INJEÇÃO DE CSS ---

    def linha_suave():
        st.markdown("<hr style='margin: 1rem 0; border: none; border-top: 1px solid rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

    # ALERTA DE NOVO NOTAM
    if str(dados.get('id')) in st.session_state.get('novos_ids', []):
        st.success("✨ **NOVO:** Notificação recente!")
        linha_suave()

    # IDENTIFICAÇÃO PRINCIPAL (Linha 1)
    col1, col2, col3, col4 = st.columns(4, gap="small")
    col1.metric("Localidade", dados.get('loc', '-'))
    col2.metric("Tipo", dados.get('tp', '-'))
    col3.metric("Número", dados.get('n', '-'))
    
    ref_val = str(dados.get('ref', '')).strip()
    col4.metric("Referência", ref_val if ref_val and ref_val not in ['nan', 'None'] else "-")

    linha_suave()

    # ASSUNTO E CONDIÇÃO (Linha 2)
    c_assunto, c_cond = st.columns(2, gap="small")
    
    c_assunto.metric("Assunto", dados.get('assunto_desc', 'N/A'))
        
    cond = dados.get('condicao_desc', 'N/A')
    if any(x in cond for x in ['Fechado', 'Proibido', 'Inoperante']):
        icone_cond = "🔴" 
    elif "Obras" in cond:
        icone_cond = "🟠"
    else:
        icone_cond = "🟢"
        
    c_cond.metric("Condição", f"{icone_cond} {cond}")

    linha_suave()

    # LINHA DO TEMPO: INÍCIO E FIM (Linha 3)
    data_b = formatters.formatar_data_notam(dados.get('b'))
    data_c = formatters.formatar_data_notam(dados.get('c'))

    c_ini, c_fim = st.columns(2, gap="small")
    c_ini.metric("Início (b)", f"📅 {data_b}")
    
    fim_str = f"🛑 {data_c}" if "PERM" in str(data_c) else f"📅 {data_c}"
    c_fim.metric("Fim (c)", fim_str)

    # PERÍODO
    periodo = str(dados.get('d', '')).strip()
    if periodo and periodo not in ['nan', 'None']:
        linha_suave()
        st.metric("Período (d)", f"🕒 {periodo}")

    linha_suave()

    # TEXTO PRINCIPAL DO NOTAM
    st.markdown("**<span style='color: #808080; font-size: 0.9rem;'>Texto (e)</span>**", unsafe_allow_html=True)
    texto_e = str(dados.get('e', 'Sem texto')).strip()
    
    st.markdown(
        f"""
        <div style='
            background-color: rgba(128, 128, 128, 0.15);
            padding: 12px 16px;
            border-radius: 8px;
            border-left: 5px solid #FF4B4B;
            font-family: "Source Code Pro", monospace;
            font-size: 15px; 
            font-weight: 500;
            white-space: pre-wrap;
            line-height: 1.4;
            margin-bottom: 0.5rem;
            min-height: 90px;
        '>{texto_e}</div>
        """,
        unsafe_allow_html=True
    )

    linha_suave()

    # DADOS BRUTOS (JSON)
    with st.expander("🔍 Ver JSON Bruto"):
        json_data = dados.to_dict() if hasattr(dados, 'to_dict') else dict(dados)
        st.json(json_data)












st.divider()

# ==============================================================================
# 1. CARREGAR DADOS E CONFIGURAÇÕES
# ==============================================================================
df_total = db_manager.carregar_notams()
meus_aeroportos = db_manager.carregar_frota_monitorada()

# ==============================================================================
# 2. BARRA DE COMANDO E STATUS (HEADER)
# ==============================================================================
with st.container(border=True):
    c_action, c_status, c_metrics = st.columns([0.20, 0.55, 0.25], gap="medium", vertical_alignment="center")

    with c_action:
        if st.button("🔄 Sincronizar", type="primary", use_container_width=True, help="Atualiza todos os NOTAMs."):
            processar_atualizacao = True
        else:
            processar_atualizacao = False

    with c_status:
        qtd_frota = len(meus_aeroportos)
        hora_utc = datetime.now(timezone.utc).strftime("%H:%M UTC")
        
        if qtd_frota > 0:
            st.caption(f"📡 AISWEB: **{qtd_frota} Aeroportos** rastreados. (Atualizado: {hora_utc})")
        else:
            st.error("⚠️ **Alerta:** Nenhuma Aeroporto configurado. O banco ficará vazio.")
            st.caption("Vá em 'Configurações' para adicionar aeroportos.")

    with c_metrics:
        if not df_total.empty:
            ultimo_dt = df_total['dt'].max() if 'dt' in df_total.columns else "-"
            data_fmt = formatters.formatar_data_notam(ultimo_dt)
            
            st.metric(
                label="NOTAMs monitorados:", 
                value=len(df_total),
                delta=f"Último NOTAM Adicionado: {data_fmt}",
                delta_color="off"
            )
        else:
            st.metric("NOTAMs Armazenados", 0, delta="Banco Vazio")

    if processar_atualizacao:
        if not meus_aeroportos:
            st.toast("⚠️ Configure seus Aeroportos antes de atualizar!", icon="🚫")
        else:
            ids_antigos = set(df_total['id'].astype(str).tolist()) if not df_total.empty and 'id' in df_total.columns else set()
            df_brasil = api_decea.buscar_firs_brasil()
            
            if df_brasil is not None and not df_brasil.empty:
                df_salvar = df_brasil[df_brasil['loc'].isin(meus_aeroportos)].copy()
                
                if not df_salvar.empty:
                    db_manager.salvar_notams(df_salvar)
                    if 'id' in df_salvar.columns:
                        ids_atuais = set(df_salvar['id'].astype(str).tolist())
                        diferenca = ids_atuais - ids_antigos
                        st.session_state['novos_ids'] = list(diferenca)
                        qtd_novos = len(diferenca)
                    else:
                        qtd_novos = 0
                    
                    st.success(f"✅ Processo concluído! {len(df_salvar)} NOTAMs salvos. ({qtd_novos} novos)")
                    st.rerun()
                else:
                    st.warning(f"A API trouxe {len(df_brasil)} NOTAMs do Brasil, mas nenhum pertence à sua lista de {qtd_frota} aeroportos.")
            elif df_brasil is None:
                st.error("Erro ao conectar com a API do DECEA.")
            else:
                st.warning("API retornou vazia.")

st.write("") 

# ==============================================================================
# 3. EXIBIÇÃO DOS DADOS
# ==============================================================================

if not df_total.empty:
    
    df_filtrado = df_total.copy()

    # --- ORDENAÇÃO ---
    if 'dt' in df_filtrado.columns:
        df_filtrado = df_filtrado.sort_values(by='dt', ascending=False)

    # ==============================================================================
    # 🕵️‍♂️ FILTROS AVANÇADOS (Ocupam toda a largura agora)
    # ==============================================================================
    with st.expander("🔎 Filtros Avançados", expanded=True):
        f1, f2, f3 = st.columns(3)
        
        locs_disponiveis = sorted(df_filtrado['loc'].unique())
        sel_loc = f1.multiselect("📍 Localidade (loc)", locs_disponiveis)
        
        txt_num = f2.text_input("🔢 Número (n)", placeholder="Ex: 1234")

        assuntos_disp = sorted(df_filtrado['assunto_desc'].unique())
        sel_subj = f3.multiselect("📂 Assunto", assuntos_disp)

        f4, f5 = st.columns(2)

        if sel_subj:
            conds_validas = df_filtrado[df_filtrado['assunto_desc'].isin(sel_subj)]['condicao_desc'].unique()
        else:
            conds_validas = df_filtrado['condicao_desc'].unique()
            
        sel_cond = f4.multiselect("🔧 Condição", sorted(conds_validas))

        txt_busca = f5.text_input("📝 Procurar no Texto (e)", placeholder="Digite palavra chave...")

    # --- APLICAÇÃO DOS FILTROS ---
    df_view = df_filtrado.copy()

    if sel_loc: df_view = df_view[df_view['loc'].isin(sel_loc)]
    if txt_num: df_view = df_view[df_view['n'].astype(str).str.contains(txt_num, case=False, na=False)]
    if sel_subj: df_view = df_view[df_view['assunto_desc'].isin(sel_subj)]
    if sel_cond: df_view = df_view[df_view['condicao_desc'].isin(sel_cond)]
    if txt_busca: df_view = df_view[df_view['e'].astype(str).str.contains(txt_busca, case=False, na=False)]

    # --- FORMATAÇÃO VISUAL ---
    if 'dt' in df_view.columns:
        df_view['dt'] = df_view['dt'].apply(formatters.formatar_data_notam)

    cols_show = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'dt']
    cols_validas = [c for c in cols_show if c in df_view.columns]
    
    st.caption(f"Exibindo {len(df_view)} registros")

    # --- ESTILO ---
    def realcar_novos(row):
        cor = ''
        if 'id' in row.index: 
            notam_id = str(row['id'])
        elif 'id' in df_view.columns:
            return [''] * len(row)
        else:
            return [''] * len(row)

        if notam_id in st.session_state['novos_ids']:
            cor = 'background-color: #d1e7dd; color: #0f5132; font-weight: bold'
        return [cor] * len(row)

    cols_para_tabela = list(cols_validas)
    if 'id' not in cols_para_tabela:
        cols_para_tabela.append('id')
        
    styler = df_view[cols_para_tabela].style.apply(realcar_novos, axis=1)
    column_config = {"id": None}

    # --- TABELA EM LARGURA TOTAL ---
    # Removemos st.columns, então a tabela usa o layout="wide" da página
    evento = st.dataframe(
        styler,
        column_config=column_config,
        use_container_width=True, 
        height=700, # Aumentei um pouco a altura já que temos mais espaço
        on_select="rerun", 
        selection_mode="single-row",
        hide_index=True
    )

    # --- LÓGICA DE DISPARO DO POP-UP ---
    if len(evento.selection.rows) > 0:
        idx = evento.selection.rows[0]
        dados_selecionados = df_view.iloc[idx]
        
        # Chama a função decorada com @st.dialog
        exibir_detalhes_popup(dados_selecionados)

else:
    if not meus_aeroportos:
        st.warning("⚠️ Você não tem aeroportos configurados.")
        st.info("Vá no menu 'Configurações' e adicione os códigos ICAO (ex: SBGR, SBRJ) que deseja monitorar.")
    else:
        st.info("Banco de dados vazio. Clique em 'Sincronizar Aeroportos' para baixar os dados.")