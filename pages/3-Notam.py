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

# Inicializa a lista de novos notams na sessão se não existir
if 'novos_ids' not in st.session_state:
    st.session_state['novos_ids'] = []

st.divider()

# 1. CONTROLE DE ATUALIZAÇÃO E LÓGICA DE DIFF
col_btn, col_info = st.columns([1, 3])
with col_btn:
    if st.button("🔄 Atualizar", type="primary", use_container_width=True):
        # 1. Carrega os IDs que já existem no banco ANTES de atualizar
        df_antigo = db_manager.carregar_notams()
        if not df_antigo.empty and 'id' in df_antigo.columns:
            # Cria um conjunto (set) com os IDs antigos para comparação rápida
            ids_antigos = set(df_antigo['id'].astype(str).tolist())
        else:
            ids_antigos = set()

        # 2. Busca os dados novos na API
        df_novo = api_decea.buscar_firs_brasil()
        
        if df_novo is not None:
            # 3. Salva no banco (substituindo o antigo)
            db_manager.salvar_notams(df_novo)
            
            # 4. Descobre quais são os novos (Diferença de Conjuntos)
            # Pega os IDs que estão no df_novo mas NÃO estavam no ids_antigos
            if 'id' in df_novo.columns:
                ids_atuais = set(df_novo['id'].astype(str).tolist())
                diferenca = ids_atuais - ids_antigos
                st.session_state['novos_ids'] = list(diferenca) # Guarda na sessão
                qtd_novos = len(diferenca)
            else:
                qtd_novos = 0
            
            if qtd_novos > 0:
                st.success(f"Base atualizada! {len(df_novo)} total. 🎉 {qtd_novos} novos NOTAMs encontrados!")
            else:
                st.success(f"Base atualizada! {len(df_novo)} total. Nenhum NOTAM novo.")
            
            st.rerun()

# 2. CARREGAR DADOS DO BANCO
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
        # Mostra quantos novos existem na visualização atual
        novos_visiveis = 0
        if 'id' in df_filtrado.columns:
            novos_visiveis = df_filtrado['id'].astype(str).isin(st.session_state['novos_ids']).sum()
            
        delta_msg = f"+{novos_visiveis} Novos" if novos_visiveis > 0 else "Sem novidades"
        st.metric("NOTAMs do Filtro", len(df_filtrado), delta=delta_msg)

    st.divider()

    # Layout Master-Detail
    col_tabela, col_detalhes = st.columns([0.60, 0.40], gap="large")

    with col_tabela:
        # --- ORDENAÇÃO INICIAL ---
        if 'dt' in df_filtrado.columns:
            df_filtrado = df_filtrado.sort_values(by='dt', ascending=False)

        # ==============================================================================
        # 🕵️‍♂️ ÁREA DE FILTROS AVANÇADOS
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

        if sel_loc:
            df_view = df_view[df_view['loc'].isin(sel_loc)]
        if txt_num:
            df_view = df_view[df_view['n'].astype(str).str.contains(txt_num, case=False, na=False)]
        if sel_subj:
            df_view = df_view[df_view['assunto_desc'].isin(sel_subj)]
        if sel_cond:
            df_view = df_view[df_view['condicao_desc'].isin(sel_cond)]
        if txt_busca:
            df_view = df_view[df_view['e'].astype(str).str.contains(txt_busca, case=False, na=False)]

        # ==============================================================================

        # Formatação Visual da Data
        if 'dt' in df_view.columns:
            df_view['dt'] = df_view['dt'].apply(formatters.formatar_data_notam)

        # Definição das Colunas
        cols_show = ['loc', 'n', 'assunto_desc', 'condicao_desc', 'dt']
        cols_validas = [c for c in cols_show if c in df_view.columns]
        
        st.caption(f"Exibindo {len(df_view)} registros")

        # --- ESTILIZAÇÃO CONDICIONAL (COLORIR LINHAS NOVAS) ---
        def realcar_novos(row):
            # Verifica se o ID da linha está na lista de novos da sessão
            # Precisamos usar o dataframe original df_view para pegar o ID, 
            # pois 'cols_validas' pode não ter a coluna 'id' visível.
            
            # Nota: O Pandas Styler itera linha a linha. 
            # Se 'id' não estiver nas colunas visíveis, precisamos garantir que ele esteja no index ou acessível.
            # Aqui, vou assumir que 'id' existe no df_view (que é uma cópia filtrada).
            
            cor = ''
            if 'id' in row.index:
                notam_id = str(row['id'])
                if notam_id in st.session_state['novos_ids']:
                    # Verde Claro suave para linhas novas
                    cor = 'background-color: #d1e7dd; color: #0f5132; font-weight: bold'
            
            return [cor] * len(row)

        # Prepara o dataframe para exibição (garantindo que 'id' está disponível para a função de estilo)
        # Se 'id' não estiver em cols_validas, adicionamos temporariamente para o styler e ocultamos depois?
        # O Streamlit dataframe aceita o objeto Styler.
        
        # Estratégia: Passamos o DF completo para o Styler, mas selecionamos as colunas depois? 
        # Não, o Styler deve ser feito nas colunas finais.
        # Vamos garantir que 'id' esteja no df_final para a lógica funcionar, mas usamos column_config para esconder se necessário
        # Ou simplesmente aplicamos o estilo baseando-se no índice se o índice for preservado.
        
        # Solução simples: Vamos aplicar o estilo antes de cortar as colunas? Não, o styler retorna um objeto Styler.
        
        # Vamos fazer o seguinte: adicionar 'id' às colunas válidas temporariamente para o cálculo, 
        # mas infelizmente o st.dataframe mostra tudo que está no styler.
        
        # WORKAROUND: Vamos criar o Styler apenas nas colunas visíveis, mas acessando o ID externamente?
        # Difícil no Pandas. O jeito mais fácil é deixar a coluna ID no dataframe mas oculta na config do Streamlit?
        # Ou melhor: Use a função apply com axis=1.
        
        # Vamos adicionar 'id' ao df_display apenas para a lógica, e torcer para o Pandas Styler permitir.
        df_display = df_view[cols_validas].copy()
        # Adiciona o ID ao df_display recuperando do índice original, caso não esteja nas colunas visíveis
        df_display['id'] = df_view['id'] 
        
        styler = df_display.style.apply(realcar_novos, axis=1)
        
        # Configuração de colunas para ESCONDER o ID técnico da visualização final
        column_config = {
            "id": None, # Isso esconde a coluna ID
        }

        # Mostra a tabela estilizada
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
            # Como o df_display pode ter sido reordenado ou filtrado, o índice do evento (linha visual 0, 1, 2)
            # mapeia para o índice do DataFrame exibido.
            
            # CUIDADO: Ao usar Styler, o index pode se comportar diferente dependendo da versão.
            # O .iloc no df_display deve funcionar.
            dados = df_display.iloc[idx] # Usamos df_display que tem o 'id' e tudo mais

            st.markdown("### 📌 Detalhes do NOTAM")
            
            # Badge de "NOVO" no detalhe também
            if str(dados.get('id')) in st.session_state['novos_ids']:
                st.success("✨ ESTE NOTAM É NOVO! (Acabou de chegar)")
            
            st.divider()

            st.markdown(f"**Localidade (loc):**")
            st.markdown(f"## 📍 {dados.get('loc', '-')}")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Tipo (tp):**")
                # Busca no df_total original para garantir que temos campos que talvez não estejam na tabela (como tp)
                # Usamos o ID para buscar a linha completa no df_view (que tem todas as colunas)
                dado_completo = df_view[df_view['id'] == dados['id']].iloc[0]
                
                st.info(f"{dado_completo.get('tp', '-')}")
            with c2:
                st.markdown("**Número (n):**")
                st.info(f"{dado_completo.get('n', '-')}")

            ref_val = dado_completo.get('ref', '')
            if ref_val and ref_val != 'nan' and ref_val != 'None':
                st.markdown(f"**Referência (ref):** {ref_val}")
            
            st.write("")

            st.markdown(f"**Assunto:**")
            st.markdown(f"##### :{'green'}[{dado_completo.get('assunto_desc', 'N/A')}]")

            cond = dado_completo.get('condicao_desc', 'N/A')
            cor = "red" if any(x in cond for x in ['Fechado','Proibido','Inoperante']) else "orange" if "Obras" in cond else "green"
            
            st.markdown(f"**Condição:**")
            st.markdown(f"##### :{cor}[{cond}]")

            st.divider()

            data_b = formatters.formatar_data_notam(dado_completo.get('b'))
            data_c = formatters.formatar_data_notam(dado_completo.get('c'))

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

            periodo = dado_completo.get('d', '')
            if periodo and periodo != 'nan' and periodo != 'None':
                st.markdown("**Período (d):**")
                st.warning(f"🕒 {periodo}")

            st.divider()

            st.markdown("**Texto (e):**")
            texto_e = dado_completo.get('e', 'Sem texto')
            
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
                # Mostra o dicionário completo do dado original
                st.json(dado_completo.to_dict())

        else:
            st.info("👈 Selecione um NOTAM na tabela para ver os detalhes.")

else:
    st.info("Banco vazio.")