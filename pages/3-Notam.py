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

# Inicializa state para highlight
if 'novos_ids' not in st.session_state:
    st.session_state['novos_ids'] = []

st.divider()

# ==============================================================================
# 1. CARREGAR DADOS E CONFIGURAÇÕES
# ==============================================================================
df_total = db_manager.carregar_notams()
meus_aeroportos = db_manager.carregar_frota_monitorada()

# ==============================================================================
# 2. CONTROLE DE ATUALIZAÇÃO (FILTER-BEFORE-SAVE)
# ==============================================================================
col_btn, col_info = st.columns([1, 3])

with col_btn:
    # Botão agora chama a função das FIRs
    if st.button("🔄 Atualizar Base Brasil", type="primary", use_container_width=True):
        if not meus_aeroportos:
            st.warning("⚠️ Adicione aeroportos em 'Configurações' antes de atualizar.")
        else:
            # 1. Snapshot dos IDs antigos
            ids_antigos = set(df_total['id'].astype(str).tolist()) if not df_total.empty and 'id' in df_total.columns else set()

            # 2. Busca o BRASIL TODO (5 FIRs)
            df_brasil = api_decea.buscar_firs_brasil()
            
            if df_brasil is not None and not df_brasil.empty:
                
                # --- FILTRO CRÍTICO ---
                # Só mantemos o que está na nossa lista de interesse
                df_salvar = df_brasil[df_brasil['loc'].isin(meus_aeroportos)].copy()
                # ----------------------

                if not df_salvar.empty:
                    # 3. Salva apenas o filtrado no banco
                    db_manager.salvar_notams(df_salvar)
                    
                    # 4. Calcula diferença (Highlight)
                    if 'id' in df_salvar.columns:
                        ids_atuais = set(df_salvar['id'].astype(str).tolist())
                        diferenca = ids_atuais - ids_antigos
                        st.session_state['novos_ids'] = list(diferenca)
                        qtd_novos = len(diferenca)
                    else:
                        qtd_novos = 0
                    
                    msg_extra = f"🎉 {qtd_novos} novos!" if qtd_novos > 0 else ""
                    st.success(f"Filtro aplicado! De {len(df_brasil)} baixados, salvamos {len(df_salvar)} da sua frota. {msg_extra}")
                    st.rerun()
                else:
                    st.warning(f"Baixamos {len(df_brasil)} NOTAMs do Brasil, mas nenhum deles é dos aeroportos da sua lista.")
            
            elif df_brasil is not None:
                st.warning("A API do DECEA não retornou dados.")
            else:
                st.error("Falha na conexão com o DECEA.")

# ==============================================================================
# 3. EXIBIÇÃO DOS DADOS
# ==============================================================================

if not df_total.empty:
    
    # O banco já está filtrado, então mostramos tudo que tem nele
    df_filtrado = df_total.copy()

    with col_info:
        novos_visiveis = 0
        if 'id' in df_filtrado.columns:
            novos_visiveis = df_filtrado['id'].astype(str).isin(st.session_state['novos_ids']).sum()
            
        delta_msg = f"+{novos_visiveis} Novos" if novos_visiveis > 0 else "Atualizado"
        st.metric("NOTAMs Ativos (Frota)", len(df_filtrado), delta=delta_msg)

    st.divider()

    # Layout Master-Detail
    col_tabela, col_detalhes = st.columns([0.60, 0.40], gap="large")

    with col_tabela:
        # Ordenação
        if 'dt' in df_filtrado.columns:
            df_filtrado = df_filtrado.sort_values(by='dt', ascending=False)

        # --- FILTROS AVANÇADOS ---
        with st.expander("🔎 Filtros Locais", expanded=True):
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

        # Aplicação dos Filtros
        df_view = df_filtrado.copy()

        if sel_loc: df_view = df_view[df_view['loc'].isin(sel_loc)]
        if txt_num: df_view = df_view[df_view['n'].astype(str).str.contains(txt_num, case=False, na=False)]
        if sel_subj: df_view = df_view[df_view['assunto_desc'].isin(sel_subj)]
        if sel_cond: df_view = df_view[df_view['condicao_desc'].isin(sel_cond)]
        if txt_busca: df_view = df_view[df_view['e'].astype(str).str.contains(txt_busca, case=False, na=False)]

        # Formatação Visual Data
        if 'dt' in df_view.columns:
            df_view['dt'] = df_view['dt'].apply(formatters.formatar_data_notam)

        cols_show = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'dt']
        cols_validas = [c for c in cols_show if c in df_view.columns]
        
        st.caption(f"Exibindo {len(df_view)} registros")

        # Função de Estilo
        def realcar_novos(row):
            cor = ''
            if 'id' in row.index:
                notam_id = str(row['id'])
                if notam_id in st.session_state['novos_ids']:
                    cor = 'background-color: #d1e7dd; color: #0f5132; font-weight: bold'
            return [cor] * len(row)

        # Prepara dados para exibição
        cols_final = list(cols_validas)
        if 'id' not in cols_final:
            cols_final.append('id')
            
        styler = df_view[cols_final].style.apply(realcar_novos, axis=1)
        
        column_config = {"id": None} # Esconde ID

        evento = st.dataframe(
            styler,
            column_config=column_config,
            use_container_width=True, 
            height=600,
            on_select="rerun", 
            selection_mode="single-row",
            hide_index=True
        )

    # --- PAINEL DE DETALHES ---
    with col_detalhes:
        if len(evento.selection.rows) > 0:
            idx = evento.selection.rows[0]
            dados = df_view.iloc[idx]

            st.markdown("### 📌 Detalhes do NOTAM")
            
            if str(dados.get('id')) in st.session_state['novos_ids']:
                st.success("✨ ESTE NOTAM É NOVO! (Acabou de chegar)")

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
    if not meus_aeroportos:
        st.warning("⚠️ Você não tem aeroportos configurados.")
        st.info("Vá no menu 'Configurações' e adicione os códigos ICAO.")
    else:
        st.info("Banco de dados vazio. Clique em 'Atualizar Base Brasil'.")