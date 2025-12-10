import streamlit as st
import pandas as pd
from datetime import datetime, timezone # <--- Adicionado para pegar a hora UTC

# Importando módulos da pasta utils
from utils import db_manager, api_decea, formatters

st.set_page_config(page_title="Monitoramento GOL", layout="wide")
st.title("✈️ Painel de Notams")

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

# Inicializa lista de IDs novos na sessão (para o realce verde)
if 'novos_ids' not in st.session_state:
    st.session_state['novos_ids'] = []

st.divider()

# ==============================================================================
# 1. CARREGAR DADOS E CONFIGURAÇÕES
# ==============================================================================
# Carregamos antes para exibir as métricas no cabeçalho
df_total = db_manager.carregar_notams()
meus_aeroportos = db_manager.carregar_frota_monitorada()

# ==============================================================================
# 2. BARRA DE COMANDO E STATUS (HEADER)
# ==============================================================================
with st.container(border=True):
    # Layout: Ação (Botão) | Status da Estratégia | Métricas do Banco
    c_action, c_status, c_metrics = st.columns([0.20, 0.55, 0.25], gap="medium", vertical_alignment="center")

    # --- COLUNA 1: AÇÃO ---
    with c_action:
        if st.button("🔄 Sincronizar Aeroportos", type="primary", use_container_width=True, help="Baixa todas as FIRs e aplica o filtro da sua frota."):
            processar_atualizacao = True
        else:
            processar_atualizacao = False

    # --- COLUNA 2: STATUS DA ESTRATÉGIA ---
    with c_status:
        qtd_frota = len(meus_aeroportos)
        
        # Pega a hora atual em UTC para mostrar na legenda
        hora_utc = datetime.now(timezone.utc).strftime("%H:%M UTC")
        
        if qtd_frota > 0:
            # --- MUDANÇA AQUI: Adicionada a hora UTC na frase ---
            st.caption(f"📡 Status AISWEB: **{qtd_frota} Aeroportos** configurados. (Ref: {hora_utc})")
        else:
            st.error("⚠️ **Alerta:** Nenhuma Aeroporto configurado. O banco ficará vazio.")
            st.caption("Vá em 'Configurações' para adicionar aeroportos.")

    # --- COLUNA 3: MÉTRICAS ATUAIS ---
    with c_metrics:
        if not df_total.empty:
            # Pega a data do registro mais recente
            ultimo_dt = df_total['dt'].max() if 'dt' in df_total.columns else "-"
            # Formata a data completa para o delta
            data_fmt = formatters.formatar_data_notam(ultimo_dt)
            
            st.metric(
                label="NOTAMs Armazenados", 
                value=len(df_total),
                delta=f"Último notam Adicionado: {data_fmt}",
                delta_color="off"
            )
        else:
            st.metric("NOTAMs Armazenados", 0, delta="Banco Vazio")

    # --- LÓGICA DE ATUALIZAÇÃO (FILTER-BEFORE-SAVE) ---
    if processar_atualizacao:
        if not meus_aeroportos:
            st.toast("⚠️ Configure seus Aeroportos antes de atualizar!", icon="🚫")
        else:
            # 1. Snapshot dos IDs antigos (para saber o que é novo)
            ids_antigos = set(df_total['id'].astype(str).tolist()) if not df_total.empty and 'id' in df_total.columns else set()

            # 2. Busca Brasil (5 FIRs)
            df_brasil = api_decea.buscar_firs_brasil()
            
            if df_brasil is not None and not df_brasil.empty:
                # 3. Filtra na memória (O Pulo do Gato 🐱) - Só salva o que importa
                df_salvar = df_brasil[df_brasil['loc'].isin(meus_aeroportos)].copy()
                
                if not df_salvar.empty:
                    # 4. Salva Filtrado
                    db_manager.salvar_notams(df_salvar)
                    
                    # 5. Calcula Novos (Diff)
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

st.write("") # Espaço de respiro

# ==============================================================================
# 3. EXIBIÇÃO DOS DADOS
# ==============================================================================

if not df_total.empty:
    
    df_filtrado = df_total.copy() # O banco já está filtrado pela regra de negócio

    # Layout Master-Detail
    col_tabela, col_detalhes = st.columns([0.60, 0.40], gap="large")

    with col_tabela:
        # --- ORDENAÇÃO (Mais recente primeiro) ---
        if 'dt' in df_filtrado.columns:
            df_filtrado = df_filtrado.sort_values(by='dt', ascending=False)

        # ==============================================================================
        # 🕵️‍♂️ FILTROS AVANÇADOS
        # ==============================================================================
        with st.expander("🔎 Filtros Avançados", expanded=True):
            f1, f2, f3 = st.columns(3)
            
            locs_disponiveis = sorted(df_filtrado['loc'].unique())
            sel_loc = f1.multiselect("📍 Localidade (loc)", locs_disponiveis)
            
            txt_num = f2.text_input("🔢 Número (n)", placeholder="Ex: 1234")

            assuntos_disp = sorted(df_filtrado['assunto_desc'].unique())
            sel_subj = f3.multiselect("📂 Assunto", assuntos_disp)

            f4, f5 = st.columns(2)

            # Filtro Condicional: Mostra condições baseadas no assunto escolhido
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
        # Formata data para tabela
        if 'dt' in df_view.columns:
            df_view['dt'] = df_view['dt'].apply(formatters.formatar_data_notam)

        cols_show = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'dt']
        
        # Garante que as colunas existem
        cols_validas = [c for c in cols_show if c in df_view.columns]
        
        st.caption(f"Exibindo {len(df_view)} registros")

        # --- ESTILO (HIGHLIGHT DE NOVOS) ---
        def realcar_novos(row):
            cor = ''
            # Verifica se 'id' está disponível no índice ou coluna
            if 'id' in row.index: 
                notam_id = str(row['id'])
            elif 'id' in df_view.columns: # Fallback se não estiver na row do styler subset
                # Tenta pegar pelo índice se o index for preservado (arriscado no styler subset)
                return [''] * len(row)
            else:
                return [''] * len(row)

            if notam_id in st.session_state['novos_ids']:
                cor = 'background-color: #d1e7dd; color: #0f5132; font-weight: bold'
            
            return [cor] * len(row)

        # Prepara dataframe para o Styler (inclui ID para a lógica funcionar)
        cols_para_tabela = list(cols_validas)
        if 'id' not in cols_para_tabela:
            cols_para_tabela.append('id')
            
        # Aplica estilo
        styler = df_view[cols_para_tabela].style.apply(realcar_novos, axis=1)
        
        # Configura para esconder a coluna ID visualmente
        column_config = {"id": None}

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
            # Usa df_view pois é o que está sincronizado com a tabela
            dados = df_view.iloc[idx]

            st.markdown("### 📌 Detalhes do NOTAM")
            
            if str(dados.get('id')) in st.session_state['novos_ids']:
                st.success("✨ **NOVO:** Notificação recente!")

            st.divider()

            # 1. Localidade
            st.markdown(f"**Localidade (loc):**")
            st.markdown(f"## 📍 {dados.get('loc', '-')}")

            # 2. Tipo e 3. Número
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Tipo (tp):**")
                st.info(f"{dados.get('tp', '-')}")
            with c2:
                st.markdown("**Número (n):**")
                st.info(f"{dados.get('n', '-')}")

            # 4. Referência
            ref_val = dados.get('ref', '')
            if ref_val and ref_val not in ['nan', 'None', '']:
                st.markdown(f"**Referência (ref):** {ref_val}")
            
            st.write("")

            # 5. Assunto
            st.markdown(f"**Assunto:**")
            st.markdown(f"##### :{'green'}[{dados.get('assunto_desc', 'N/A')}]")

            # 6. Condição
            cond = dados.get('condicao_desc', 'N/A')
            cor = "red" if any(x in cond for x in ['Fechado','Proibido','Inoperante']) else "orange" if "Obras" in cond else "green"
            
            st.markdown(f"**Condição:**")
            st.markdown(f"##### :{cor}[{cond}]")

            st.divider()

            # 7. Início e 8. Fim
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

            # 9. Período
            periodo = dados.get('d', '')
            if periodo and periodo not in ['nan', 'None', '']:
                st.markdown("**Período (d):**")
                st.warning(f"🕒 {periodo}")

            st.divider()

            # 10. Texto
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
    # Se o banco estiver vazio, verifica a lista para dar a dica certa
    if not meus_aeroportos:
        st.warning("⚠️ Você não tem aeroportos configurados.")
        st.info("Vá no menu 'Configurações' e adicione os códigos ICAO (ex: SBGR, SBRJ) que deseja monitorar.")
    else:
        st.info("Banco de dados vazio. Clique em 'Sincronizar Aeroportos' para baixar os dados.")