import pandas as pd
from utils import parser_notam

def gerar_cronograma_detalhado(df_criticos):
    """
    Recebe o DataFrame de NOTAMs Críticos e explode os horários
    utilizando o algoritmo robusto de parsing (V24).
    
    Retorna: DataFrame com colunas [Localidade, NOTAM, Assunto, Condição, Inicio, Fim]
    """
    lista_expandida = []

    if df_criticos.empty:
        return pd.DataFrame()

    # Itera sobre cada NOTAM crítico encontrado
    for index, row in df_criticos.iterrows():
        
        # 1. Extrai dados básicos
        icao = row.get('loc', '')
        num_notam = row.get('n', '')
        assunto = row.get('assunto_desc', '')
        condicao = row.get('condicao_desc', '')
        
        # Campos crus para o Parser
        item_b = row.get('b', '') # Data Início Raw (YYMMDDHHMM)
        item_c = row.get('c', '') # Data Fim Raw
        item_d = row.get('d', '') # Texto do Período
        
        # 2. Chama o Algoritmo Robusto (V24)
        # Se tiver Item D, o parser resolve a complexidade (DLY, EXC, SR-SS...)
        if item_d and str(item_d).strip() not in ['nan', 'None', '']:
            slots = parser_notam.interpretar_periodo_atividade(item_d, icao, item_b, item_c)
        else:
            # 3. Fallback: Se NÃO tem Item D (ex: Fechamento contínuo/PERM)
            # Criamos um único slot do Inicio (B) ao Fim (C)
            dt_ini = parser_notam.parse_notam_date(item_b)
            dt_fim = parser_notam.parse_notam_date(item_c)
            
            # Se não conseguiu ler as datas, pula
            if not dt_ini:
                continue
                
            # Se não tem fim (PERM), define horizonte padrão (ex: +30 dias ou exibe PERM)
            if not dt_fim: 
                # Opção: Jogar para longe ou marcar flag. Vamos projetar 30 dias.
                from datetime import timedelta
                dt_fim = dt_ini + timedelta(days=30) 

            slots = [{'inicio': dt_ini, 'fim': dt_fim}]

        # 4. Expande a lista principal com os slots calculados
        for slot in slots:
            lista_expandida.append({
                'Localidade': icao,
                'NOTAM': num_notam,
                'Assunto': assunto,
                'Condição': condicao,
                'Data Inicial': slot['inicio'], # Objeto datetime real
                'Data Final': slot['fim']       # Objeto datetime real
            })

    # 5. Cria DataFrame Final
    df_timeline = pd.DataFrame(lista_expandida)
    
    # Ordena por Data e Localidade para facilitar leitura
    if not df_timeline.empty:
        df_timeline = df_timeline.sort_values(by=['Data Inicial', 'Localidade'])

    return df_timeline