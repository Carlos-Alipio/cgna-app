import pandas as pd
from datetime import datetime, timedelta
from utils import parser_notam

def gerar_cronograma_detalhado(df_criticos):
    """
    Recebe o DataFrame de NOTAMs Críticos e explode os horários.
    """
    lista_expandida = []

    if df_criticos.empty:
        return pd.DataFrame()

    for index, row in df_criticos.iterrows():
        
        # Extração dos Dados
        icao = row.get('loc', '')
        num_notam = row.get('n', '')
        assunto = row.get('assunto_desc', '')
        condicao = row.get('condicao_desc', '')
        
        # Campos de Data/Texto
        item_b_raw = row.get('b', '')
        item_c_raw = row.get('c', '')
        item_d_text = str(row.get('d', '')).strip()
        item_e_text = row.get('e', '') 

        slots = []

        # 1. Tenta Interpretar o Item D (Parser de Horários Complexos)
        tem_texto_d = item_d_text and item_d_text.upper() not in ['NONE', 'NAN', '']
        
        if tem_texto_d:
            slots = parser_notam.interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw)

        # 2. Fallback (Se não achou horários no texto)
        if not slots:
            dt_ini = parser_notam.parse_notam_date(item_b_raw)
            dt_fim = parser_notam.parse_notam_date(item_c_raw)
            
            if dt_ini:
                # Se a Data Final for Nula ou Inválida, aplicamos a regra
                if not dt_fim: 
                    # --- REGRA ESTRITA SOLICITADA ---
                    # Verifica APENAS se tem "PERM" no campo C
                    if "PERM" in str(item_c_raw).upper():
                        dt_fim = dt_ini + timedelta(days=365) # 1 Ano
                    else:
                        dt_fim = dt_ini + timedelta(hours=1)  # 1 Hora (Padrão mínimo)
                
                # Correção simples caso a data final venha menor que a inicial (erro de dado)
                elif dt_fim < dt_ini:
                     dt_fim = dt_ini + timedelta(hours=24)

                slots.append({'inicio': dt_ini, 'fim': dt_fim})

        # Adiciona ao Relatório Final
        for slot in slots:
            lista_expandida.append({
                'Localidade': icao,
                'NOTAM': num_notam,
                'Assunto': assunto,
                'Condição': condicao,
                'Data Inicial': slot['inicio'],
                'Data Final': slot['fim'],
                'Texto': item_e_text 
            })

    # Gera DataFrame Final
    df_timeline = pd.DataFrame(lista_expandida)
    
    if not df_timeline.empty:
        df_timeline = df_timeline.sort_values(by=['Data Inicial', 'Localidade'])

    return df_timeline

def filtrar_por_turno(df_timeline, data_referencia, turno):
    """
    Filtra os NOTAMs que colidem com o horário do turno selecionado.
    """
    if df_timeline.empty:
        return pd.DataFrame(), ""

    # 1. Definição dos Horários do Turno (UTC)
    hora_inicio = 0
    turno_upper = turno.upper()
    
    if 'MADRUGADA' in turno_upper: 
        hora_inicio = 3
    elif 'MANHA' in turno_upper or 'MANHÃ' in turno_upper:   
        hora_inicio = 9
    elif 'TARDE' in turno_upper:   
        hora_inicio = 15
    elif 'NOITE' in turno_upper:   
        hora_inicio = 21

    # Cria datetime inicial do turno
    dt_turno_inicio = datetime.combine(data_referencia, datetime.min.time()) + timedelta(hours=hora_inicio)
    
    # Cria datetime final do turno (+12 horas fixas)
    dt_turno_fim = dt_turno_inicio + timedelta(hours=12)

    # 2. Lógica de Intersecção (Overlap)
    mask = (
        (df_timeline['Data Inicial'] < dt_turno_fim) & 
        (df_timeline['Data Final'] > dt_turno_inicio)
    )
    
    df_turno = df_timeline[mask].copy()
    
    periodo_str = f"{dt_turno_inicio.strftime('%d/%m %H:%M')}z até {dt_turno_fim.strftime('%d/%m %H:%M')}z"
    
    return df_turno, periodo_str