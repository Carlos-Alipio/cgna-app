import streamlit as st
import pandas as pd

# Importando nossos módulos organizados da pasta utils
from utils import db_manager, api_decea, formatters

st.set_page_config(page_title="Monitoramento GOL", layout="wide")
st.title("✈️ Painel de Operações (Modular)")

# --- SEGURANÇA ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.error("Acesso Negado.")
    st.stop()

st.divider()

# 1. CONTROLE DE ATUALIZAÇÃO
col_btn, col_info = st.columns([1, 3])
with col_btn:
    if st.button("🔄 Atualizar Base Brasil", type="primary", use_container_width=True):
        df_novo = api_decea.buscar_firs_brasil()
        if df_novo is not None:
            db_manager.salvar_notams(df_novo)
            st.success(f"Base atualizada! {len(df_novo)} NOTAMs.")
            st.rerun()

# 2. CARREGAR E FILTRAR
df_total = db_manager.carregar_notams()
meus_aeroportos = db_manager.carregar_frota_monitorada()

if not df_total.empty:
    
    # Lógica de visualização
    if meus_aeroportos:
        df_filtrado = df_total[df_total['loc'].isin(meus_aeroportos)]
    else:
        st.warning("⚠️ Lista de monitoramento vazia. Vá em Configurações.")
        df_filtrado = df_total

    with col_info:
        st.metric("NOTAMs da Frota", len(df_filtrado), delta=f"Total Brasil: {len(df_total)}")

    st.divider()

# Layout Master-Detail
    col_tabela, col_detalhes = st.columns([0.60, 0.40], gap="large")

    with col_tabela:
        # 1. ORDENAÇÃO (Novo)
        # Ordena pela coluna 'dt' (data do notam) do mais novo para o mais antigo
        # Convertemos para string para garantir, caso venha misturado
        if 'dt' in df_filtrado.columns:
            df_filtrado = df_filtrado.sort_values(by='dt', ascending=False)

        # 2. FILTROS
        assuntos = sorted(df_filtrado['assunto_desc'].unique())
        filtro = st.multiselect("Filtrar Assunto:", assuntos)
        
        # Aplica filtro visual se houver
        df_view = df_filtrado[df_filtrado['assunto_desc'].isin(filtro)] if filtro else df_filtrado
        
        # 3. COLUNAS (Modificado: Sai b/c, entra dt)
        cols_show = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'dt']
        
        # Garante que as colunas existem antes de mostrar
        cols_validas = [c for c in cols_show if c in df_view.columns]
        
        # Seletor de colunas (para o usuário poder trazer 'b' e 'c' de volta se quiser)
        cols_visiveis = st.multiselect(
            "👁️ Colunas visíveis:",
            options=df_view.columns,
            default=cols_validas
        )
        
        # Mostra a tabela
        evento = st.dataframe(
            df_view[cols_visiveis],
            use_container_width=True, 
            height=600,
            on_select="rerun", 
            selection_mode="single-row",
            hide_index=True
        )

    # --- PAINEL DE DETALHES (LAYOUT NOVO) ---
    with col_detalhes:
        if len(evento.selection.rows) > 0:
            idx = evento.selection.rows[0]
            dados = df_view.iloc[idx]

            st.markdown("### 📌 Detalhes do NOTAM")
            st.divider()

            # 1. Localidade (loc)
            st.markdown(f"**Localidade (loc):**")
            st.markdown(f"## 📍 {dados.get('loc', '-')}")

            # 2. Tipo e 3. Número (Agrupados para economizar espaço visual, mas claros)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Tipo (tp):**")
                st.info(f"{dados.get('tp', '-')}")
            with c2:
                st.markdown("**Número (n):**")
                st.info(f"{dados.get('n', '-')}")

            # 4. Referência (ref)
            ref_val = dados.get('ref', '')
            if ref_val and ref_val != 'nan' and ref_val != 'None':
                st.markdown(f"**Referência (ref):** {ref_val}")
            
            st.write("") # Espaço

            # 5. Assunto
            subj = dados.get('assunto_desc', 'N/A')
            st.markdown(f"**Assunto:**")
            st.markdown(f"##### {subj}")

            # 6. Condição (Com cor)
            cond = dados.get('condicao_desc', 'N/A')
            cor = "red" if any(x in cond for x in ['Fechado','Proibido','Inoperante']) else "orange" if "Obras" in cond else "green"
            
            st.markdown(f"**Condição:**")
            st.markdown(f"##### {cond}")

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

            # 9. Período (d) - Item D do NOTAM
            # Verifica se existe e não é vazio
            periodo = dados.get('d', '')
            if periodo and periodo != 'nan' and periodo != 'None':
                st.markdown("**Período (d):**")
                st.warning(f"🕒 {periodo}")

            st.divider()

            # 10. Texto (e)
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

            # JSON Técnico no final
            with st.expander("🔍 Ver JSON Bruto"):
                st.json(dados.to_dict())

        else:
            st.info("👈 Selecione um NOTAM na tabela para ver os detalhes.")

else:
    st.info("Banco vazio. Clique em 'Atualizar Base Brasil'.")