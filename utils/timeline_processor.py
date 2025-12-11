import pandas as pd
from datetime import timedelta
from utils import parser_notam

def gerar_cronograma_detalhado(df_criticos):
    """
    Recebe o DataFrame de NOTAMs Críticos.
    1. Tenta ler o Item D (Dias/Horários complexos).
    2. Se D for vazio/None, usa B e C como período único contínuo.
    """
    lista_expandida = []

    if df_criticos.empty:
        return pd.DataFrame()

    for index, row in df_criticos.iterrows():
        
        # 1. Extração dos Dados
        icao = row.get('loc', '')
        num_notam = row.get('n', '')
        assunto = row.get('assunto_desc', '')
        condicao = row.get('condicao_desc', '')
        
        # Campos de Data/Texto
        item_b_raw = row.get('b', '') # ex: '2512132000'
        item_c_raw = row.get('c', '') # ex: '2512132115'
        item_d_text = str(row.get('d', '')).strip() # ex: 'None', 'DLY...', ''

        slots = []

        # 2. Tenta Interpretar o Item D (Se não for "None")
        # Verifica se tem texto útil (ignora 'None', 'nan', '')
        tem_texto_d = item_d_text and item_d_text.upper() not in ['NONE', 'NAN', '']
        
        if tem_texto_d:
            # Tenta explodir os dias (DLY, EXC, SR-SS)
            slots = parser_notam.interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw)

        # 3. Lógica de Fallback (Plano B)
        # Se não tinha Item D, OU se o parser retornou vazio (falha ou texto inválido)
        # Devemos assumir que o NOTAM vale de B até C direto.
        if not slots:
            dt_ini = parser_notam.parse_notam_date(item_b_raw)
            dt_fim = parser_notam.parse_notam_date(item_c_raw)
            
            # Validação mínima: Precisa pelo menos da data de início
            if dt_ini:
                # Se não tem fim (ex: PERM), joga 30 dias pra frente ou usa o próprio início se for pontual
                if not dt_fim: 
                    # Se Item C for "PERM", define um horizonte visual
                    if "PERM" in str(item_c_raw).upper():
                        dt_fim = dt_ini + timedelta(days=30)
                    else:
                        # Se for erro de dado, assume fim = início (evento pontual) ou +1 hora
                        dt_fim = dt_ini + timedelta(hours=1) 
                
                # Cria o slot único
                slots.append({'inicio': dt_ini, 'fim': dt_fim})

        # 4. Adiciona ao Relatório Final
        for slot in slots:
            lista_expandida.append({
                'Localidade': icao,
                'NOTAM': num_notam,
                'Assunto': assunto,
                'Condição': condicao,
                'Data Inicial': slot['inicio'],
                'Data Final': slot['fim']
            })

    # 5. Gera DataFrame
    df_timeline = pd.DataFrame(lista_expandida)
    
    if not df_timeline.empty:
        # Ordena cronologicamente
        df_timeline = df_timeline.sort_values(by=['Data Inicial', 'Localidade'])

    return df_timeline

    def filtrar_por_turno(df_timeline, data_referencia, turno):
        """
        Filtra os NOTAMs que colidem com o horário do turno selecionado.
        Turnos (Range de 12h):
        - MADRUGADA: 00:00 - 12:00
        - MANHA:     06:00 - 18:00
        - TARDE:     12:00 - 00:00 (Dia seguinte)
        - NOITE:     18:00 - 06:00 (Dia seguinte)
        """
        if df_timeline.empty:
            return pd.DataFrame()

        # 1. Definição dos Horários do Turno
        hora_inicio = 0
        if turno == 'MADRUGADA': hora_inicio = 0
        elif turno == 'MANHA':   hora_inicio = 6
        elif turno == 'TARDE':   hora_inicio = 12
        elif turno == 'NOITE':   hora_inicio = 18

        # Cria datetime inicial do turno
        dt_turno_inicio = datetime.combine(data_referencia, datetime.min.time()) + timedelta(hours=hora_inicio)
        
        # Cria datetime final do turno (+12 horas fixas conforme regra)
        dt_turno_fim = dt_turno_inicio + timedelta(hours=12)

        # 2. Lógica de Intersecção (Overlap)
        # Regra: (InicioA < FimB) e (FimA > InicioB)
        # A = Notam, B = Turno
        
        mask = (
            (df_timeline['Data Inicial'] < dt_turno_fim) & 
            (df_timeline['Data Final'] > dt_turno_inicio)
        )
        
        df_turno = df_timeline[mask].copy()
        
        # 3. Adiciona informação visual para o relatório
        if not df_turno.empty:
            # Formata o cabeçalho do relatório
            periodo_str = f"{dt_turno_inicio.strftime('%d/%m %H:%M')} até {dt_turno_fim.strftime('%d/%m %H:%M')}"
            return df_turno, periodo_str
        
        return pd.DataFrame(), ""