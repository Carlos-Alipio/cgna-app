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

# 1. CONTROLE DE ATUALIZAÇÃO
col_btn, col_info = st.columns([1, 3])
with col_btn:
    if st.button("🔄 Atualizar", type="primary", use_container_width=True):
        df_novo = api_decea.buscar_firs_brasil()
        if df_novo is not None:
            db_manager.salvar_notams(df_novo)
            st.success(f"Base atualizada! {len(df_novo)} NOTAMs.")
            st.rerun()

# 2. CARREGAR DADOS
df_total = db_manager.carregar_notams()
meus_aeroportos = db_manager.carregar_frota_monitorada()

if not df_total.empty:
    
    # Filtro de Frota (Regra de Negócio)
    if meus_aeroportos:
        df_filtrado = df_total[df_total['loc'].isin(meus_aeroportos)].copy()
    else:
        st.warning("⚠️ Lista de monitoramento vazia.")
        df_filtrado = df_total.copy()

    with col_info:
        st.metric("NOTAMs do Filtro", len(df_filtrado), delta=f"Total AISWEB: {len(df_total)}")

    st.divider()

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