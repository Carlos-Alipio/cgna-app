import streamlit as st
import pandas as pd

# Importando módulos
from utils import db_manager, api_decea, formatters

st.set_page_config(page_title="Monitoramento GOL", layout="wide")
st.title("✈️ Painel de Notams")

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

st.divider()

# ... (código de segurança anterior) ...

# 2. CARREGAR DADOS (Carregamos ANTES de desenhar o painel para ter os números)
df_total = db_manager.carregar_notams()
meus_aeroportos = db_manager.carregar_frota_monitorada()

if not df_total.empty:
    # Filtro de Frota (Regra de Negócio)
    if meus_aeroportos:
        df_filtrado = df_total[df_total['loc'].isin(meus_aeroportos)].copy()
        modo_filtro = "Frota Monitorada"
    else:
        df_filtrado = df_total.copy()
        modo_filtro = "Sem Filtro (Tudo)"
else:
    df_filtrado = pd.DataFrame()
    modo_filtro = "-"

# ==============================================================================
# 1. 🕹️ PAINEL DE CONTROLE (LAYOUT MELHORADO)
# ==============================================================================
with st.container(border=True):
    # Dividimos em: Métricas (Esquerda) e Ação (Direita)
    col_metrics, col_btn = st.columns([0.75, 0.25], gap="large", vertical_alignment="center")
    
    with col_metrics:
        # Sub-colunas para as métricas ficarem lado a lado
        m1, m2, m3 = st.columns(3)
        
        # Métrica 1: Total Geral
        m1.metric(
            label="📦 Base Total (Brasil)", 
            value=len(df_total),
            help="Total de NOTAMs armazenados no banco de dados (todas as FIRs)."
        )
        
        # Métrica 2: Filtro Atual
        delta_val = f"{(len(df_filtrado)/len(df_total)):.1%} da base" if len(df_total) > 0 else None
        m2.metric(
            label=f"🎯 Visualizando ({len(meus_aeroportos)} ADs)", 
            value=len(df_filtrado), 
            delta=delta_val,
            help="NOTAMs filtrados apenas para a sua lista de aeroportos configurada."
        )

        # Métrica 3: Status
        m3.markdown(f"**Modo:** `{modo_filtro}`")
        if not df_total.empty:
            # Pega a data mais recente do banco para mostrar "Última atualização"
            if 'dt' in df_total.columns:
                ultima_data = df_total['dt'].max() # Pega a maior data bruta
                # Formata apenas visualmente
                m3.caption(f"📅 Dados de: {formatters.formatar_data_notam(ultima_data)}")

    with col_btn:
        # Botão destacado na direita
        st.write("") # Espaçamento para alinhar verticalmente
        if st.button("🔄 Atualizar Base (API)", type="primary", use_container_width=True, help="Baixa novamente as 5 FIRs do DECEA e atualiza o banco."):
            df_novo = api_decea.buscar_firs_brasil()
            if df_novo is not None:
                db_manager.salvar_notams(df_novo)
                st.success("Atualizado!")
                st.rerun()

st.write("") # Espaço respiro antes da tabela

if not df_total.empty:
    # ... (O código continua daqui para baixo com 'st.divider()', 'Layout Master-Detail' etc) ...


    # Layout Master-Detail
    col_tabela, col_detalhes = st.columns([0.60, 0.40], gap="large")

    with col_tabela:
        # --- ORDENAÇÃO INICIAL ---
        if 'dt' in df_filtrado.columns:
            df_filtrado = df_filtrado.sort_values(by='dt', ascending=False)

        # ==============================================================================
        # 🕵️‍♂️ ÁREA DE FILTROS AVANÇADOS (LAYOUT OTIMIZADO)
        # ==============================================================================
        with st.expander("🔎 Filtros Avançados", expanded=True):
            # Linha 1: Localidade, Número e Assunto (3 colunas)
            f1, f2, f3 = st.columns(3)
            
            # 1. Localidade (Multiselect)
            locs_disponiveis = sorted(df_filtrado['loc'].unique())
            sel_loc = f1.multiselect("📍 Localidade (loc)", locs_disponiveis)
            
            # 2. Número (Texto)
            txt_num = f2.text_input("🔢 Número (n)", placeholder="Ex: 1234")

            # 3. Assunto (Multiselect)
            assuntos_disp = sorted(df_filtrado['assunto_desc'].unique())
            sel_subj = f3.multiselect("📂 Assunto", assuntos_disp)

            # Linha 2: Condição e Texto (2 colunas)
            f4, f5 = st.columns(2)

            # 4. Condição (CONDICIONAL ao Assunto)
            # Lógica: Se escolheu Assunto, mostra só as condições daquele assunto
            if sel_subj:
                conds_validas = df_filtrado[df_filtrado['assunto_desc'].isin(sel_subj)]['condicao_desc'].unique()
            else:
                conds_validas = df_filtrado['condicao_desc'].unique()
                
            sel_cond = f4.multiselect("🔧 Condição", sorted(conds_validas))

            # 5. Texto (Texto)
            txt_busca = f5.text_input("📝 Procurar no Texto (e)", placeholder="Digite palavra chave...")

        # --- APLICAÇÃO DOS FILTROS (Lógica em Cascata) ---
        df_view = df_filtrado.copy()

        if sel_loc:
            df_view = df_view[df_view['loc'].isin(sel_loc)]
        
        if txt_num:
            # Converte para string e busca parcial
            df_view = df_view[df_view['n'].astype(str).str.contains(txt_num, case=False, na=False)]

        if sel_subj:
            df_view = df_view[df_view['assunto_desc'].isin(sel_subj)]

        if sel_cond:
            df_view = df_view[df_view['condicao_desc'].isin(sel_cond)]

        if txt_busca:
            df_view = df_view[df_view['e'].astype(str).str.contains(txt_busca, case=False, na=False)]

        # ==============================================================================

        # Formatação Visual da Data (Pós-Filtro)
        if 'dt' in df_view.columns:
            df_view['dt'] = df_view['dt'].apply(formatters.formatar_data_notam)

        # Definição das Colunas
        cols_show = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'dt']
        cols_validas = [c for c in cols_show if c in df_view.columns]
        
        st.caption(f"Exibindo {len(df_view)} registros")

        # Tabela
        evento = st.dataframe(
            df_view[cols_validas],
            use_container_width=True, height=600,
            on_select="rerun", selection_mode="single-row", hide_index=True
        )

    # --- PAINEL DE DETALHES ---
    with col_detalhes:
        if len(evento.selection.rows) > 0:
            idx = evento.selection.rows[0]
            dados = df_view.iloc[idx]

            st.markdown("### 📌 Detalhes do NOTAM")
            st.divider()

            st.markdown(f"**Localidade (loc):**")
            st.markdown(f"## 📍 {dados.get('loc', '-')}")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Tipo (tp):**")
                st.info(f"{dados.get('tp', '-')}")
            with c2:
                st.markdown("**Número (n):**")
                st.info(f"{dados.get('n', '-')}")

            ref_val = dados.get('ref', '')
            if ref_val and ref_val != 'nan' and ref_val != 'None':
                st.markdown(f"**Referência (ref):** {ref_val}")
            
            st.write("")

            st.markdown(f"**Assunto:**")
            # Sua personalização: cor verde
            st.markdown(f"##### :{'green'}[{dados.get('assunto_desc', 'N/A')}]")

            cond = dados.get('condicao_desc', 'N/A')
            cor = "red" if any(x in cond for x in ['Fechado','Proibido','Inoperante']) else "orange" if "Obras" in cond else "green"
            
            st.markdown(f"**Condição:**")
            st.markdown(f"##### :{cor}[{cond}]")

            st.divider()

            data_b = formatters.formatar_data_notam(dados.get('b'))
            data_c = formatters.formatar_data_notam(dados.get('c'))

            c_ini, c_fim = st.columns(2)
            with c_ini:
                st.markdown("**Início (b):**")
                st.write(f"📅 {data_b}")
            with c_fim:
                st.markdown("**Fim (c):**")
                if "PERM" in str(data_c):
                    st.write(f"📅 :red[{data_c}]")
                else:
                    st.write(f"📅 {data_c}")

            periodo = dados.get('d', '')
            if periodo and periodo != 'nan' and periodo != 'None':
                st.markdown("**Período (d):**")
                st.warning(f"🕒 {periodo}")

            st.divider()

            st.markdown("**Texto (e):**")
            texto_e = dados.get('e', 'Sem texto')
            
            st.markdown(
                f"""
                <div style='
                    background-color: rgba(128, 128, 128, 0.15);
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 5px solid #FF4B4B;
                    font-family: "Source Code Pro", monospace;
                    font-size: 14px;
                    white-space: pre-wrap;
                    line-height: 1.5;
                '>{texto_e.strip()}</div>
                """,
                unsafe_allow_html=True
            )

            st.divider()

            with st.expander("🔍 Ver JSON Bruto"):
                st.json(dados.to_dict())

        else:
            st.info("👈 Selecione um NOTAM na tabela para ver os detalhes.")

else:
    st.info("Banco vazio.")