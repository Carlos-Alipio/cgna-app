import re
from datetime import datetime, timedelta

# --- MAPEAMENTOS GLOBAIS ---
MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    "FEV": 2, "ABR": 4, "MAI": 5, "AGO": 8, "SET": 9, "OUT": 10, "DEZ": 12
}

WEEK_MAP = {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6,
    "SEG": 0, "TER": 1, "QUA": 2, "QUI": 3, "SEX": 4, "SAB": 5, "DOM": 6
}

def parse_notam_date(date_str):
    """Converte strings de data do NOTAM (formato B/C) para datetime."""
    try:
        if not date_str: return None
        clean_str = ''.join(filter(str.isdigit, str(date_str)))
        if len(clean_str) == 10:
            return datetime.strptime(clean_str, "%y%m%d%H%M")
        elif len(clean_str) == 12:
            return datetime.strptime(clean_str, "%Y%m%d%H%M")
        return None
    except: return None

def criar_data_segura(ano, mes, dia):
    """Cria datetime evitando erros de dia inválido (ex: 30 de Fev)."""
    try:
        return datetime(ano, mes, dia)
    except: return None

def gerar_sequencia_datas(ano_base, mes_ini, dia_ini, mes_fim, dia_fim):
    """Gera lista de datas entre dois pontos, tratando virada de ano."""
    datas = []
    dt_start = criar_data_segura(ano_base, mes_ini, dia_ini)
    dt_end = criar_data_segura(ano_base, mes_fim, dia_fim)
    
    if not dt_start or not dt_end: return []
    
    # Se o fim for menor que o início (ex: DEC a JAN), adiciona ano
    if dt_end < dt_start: 
        dt_end = dt_end.replace(year=ano_base + 1)
    
    curr = dt_start
    while curr <= dt_end:
        datas.append(curr)
        curr += timedelta(days=1)
    return datas

def ajustar_ano_referencia(dt, dt_referencia_b):
    """Ajusta o ano da data extraída com base na data de início do NOTAM."""
    if not dt: return None
    # Se a data extraída é JAN/FEB e o NOTAM começa em NOV/DEC, é ano seguinte
    if dt.month < dt_referencia_b.month and dt_referencia_b.month > 10:
        return dt.replace(year=dt_referencia_b.year + 1)
    # Se o NOTAM começa em JAN e a data é DEC (ordem não cronológica), mantém ano base
    return dt

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    Parser V18 (Production Ready)
    Capacidades:
    - Intervalos (TIL, -)
    - Listas Disjuntas
    - Semanas Cruzadas
    - Sintaxe Híbrida e Barras (JAN 17/18)
    - Filtro de Limites Exatos (B/C)
    """
    dt_b = parse_notam_date(item_b_raw)
    
    # Tratamento para PERM
    dt_c = None
    if item_c_raw and "PERM" in str(item_c_raw).upper():
        if dt_b: dt_c = dt_b + timedelta(days=365) # Default 1 ano para PERM
    else:
        dt_c = parse_notam_date(item_c_raw)

    if not dt_b or not dt_c: return []

    slots = []
    text = str(item_d_text).upper()
    text = " ".join(text.split()) # Normaliza espaços
    
    contexto_ano = dt_b.year

    # --- REGEX MASTER: Segmenta o texto por horários ---
    # Captura padrões como: "MON TUE 1000-1200" ou apenas "1000-1200"
    regex_complexo = r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{4})\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{4})'
    regex_simples = r'(\d{4})(?:-|TIL)(\d{4})'
    re_master = re.compile(f'(?:{regex_complexo})|(?:{regex_simples})')

    matches = list(re_master.finditer(text))
    last_end = 0
    
    # Contexto global que persiste entre segmentos se não for redefinido
    contexto_mes = dt_b.month
    ultima_lista_datas = [] 
    ultimo_filtro_semana = set()
    
    # Se não houver horários no texto, assume slot único B->C
    if not matches and not slots: return [{'inicio': dt_b, 'fim': dt_c}]

    for match in matches:
        c_dia_ini, c_hora_ini, c_dia_fim, c_hora_fim, s_hora_ini, s_hora_fim = match.groups()
        is_complex = (c_dia_ini is not None)
        
        offset_dias = 0
        filtro_dia_inicio = None
        
        # Determina horários e offsets de dias (para casos "MON 2200 TIL TUE 0200")
        if is_complex:
            h_ini_str, h_fim_str = c_hora_ini, c_hora_fim
            idx_ini = WEEK_MAP[c_dia_ini]
            idx_fim = WEEK_MAP[c_dia_fim]
            filtro_dia_inicio = idx_ini 
            if idx_fim >= idx_ini: offset_dias = idx_fim - idx_ini
            else: offset_dias = (7 - idx_ini) + idx_fim
        else:
            h_ini_str, h_fim_str = s_hora_ini, s_hora_fim
            # Se hora fim < hora inicio em definição simples, é overnight (+1 dia)
            if int(h_fim_str) < int(h_ini_str): offset_dias = 1

        # Texto anterior ao horário atual (contém as datas/dias)
        segmento = text[last_end:match.start()]
        last_end = match.end()
        
        datas_deste_segmento = []
        filtro_semana_deste_segmento = set()
        achou_nova_definicao = False

        # Tokeniza para processar datas e dias
        tokens = re.findall(r'[A-Za-z0-9/]+', segmento)
        
        tem_conteudo_data = any(t in MONTH_MAP or t[0].isdigit() for t in tokens)
        tem_conteudo_semana = any(t.split("/")[0] in WEEK_MAP for t in tokens)

        if tem_conteudo_data or tem_conteudo_semana:
            achou_nova_definicao = True
            
            # --- SCANNER DE DIAS DA SEMANA ---
            k = 0 
            while k < len(tokens):
                tok = tokens[k]
                # Tratamento para dias com barra (WED/THU)
                if "/" in tok and not tok[0].isdigit():
                    partes = tok.split("/")
                    for p in partes:
                        if p in WEEK_MAP: filtro_semana_deste_segmento.add(WEEK_MAP[p])
                    k += 1; continue
                
                if tok in WEEK_MAP:
                    idx_tok = WEEK_MAP[tok]
                    # Tratamento para ranges de dias (MON TIL WED)
                    if k + 2 < len(tokens) and tokens[k+1] == "TIL":
                        alvo_tok = tokens[k+2]
                        if alvo_tok in WEEK_MAP:
                            idx_alvo = WEEK_MAP[alvo_tok]
                            if idx_tok <= idx_alvo: filtro_semana_deste_segmento.update(range(idx_tok, idx_alvo + 1))
                            else: # Range cruzado (ex: SAT TIL TUE)
                                filtro_semana_deste_segmento.update(range(idx_tok, 7))
                                filtro_semana_deste_segmento.update(range(0, idx_alvo + 1))
                            k += 3; continue
                    filtro_semana_deste_segmento.add(idx_tok); k += 1
                else: k += 1
            
            # --- SCANNER DE DATAS (Range Intelligence V18) ---
            i = 0 
            while i < len(tokens):
                tok = tokens[i]
                
                # Pula tokens de semana ou 'TIL' solto já processados
                if tok in WEEK_MAP or ("/" in tok and not tok[0].isdigit()): i += 1; continue
                if tok == "TIL" and i>0 and (tokens[i-1] in WEEK_MAP or ("/" in tokens[i-1] and not tokens[i-1][0].isdigit())): i += 1; continue

                if tok in MONTH_MAP: contexto_mes = MONTH_MAP[tok]; i += 1; continue
                
                if tok[0].isdigit():
                    # Verifica Lookahead para Range (ex: 17/18 TIL 14/15)
                    if i + 2 < len(tokens) and tokens[i+1] == "TIL":
                        alvo = tokens[i+2]
                        # Pega o primeiro dia antes da barra (17/18 -> 17)
                        dia_start = int(tok.split("/")[0])
                        
                        if alvo[0].isdigit():
                            # Range no mesmo mês (10 TIL 15)
                            dia_end = int(alvo.split("/")[0])
                            datas_deste_segmento.extend(gerar_sequencia_datas(contexto_ano, contexto_mes, dia_start, contexto_mes, dia_end))
                            i += 3; continue
                        elif alvo in MONTH_MAP:
                            # Range entre meses (10 TIL FEB 15)
                            mes_dest = MONTH_MAP[alvo]
                            if i + 3 < len(tokens) and tokens[i+3][0].isdigit():
                                dia_end = int(tokens[i+3].split("/")[0])
                                datas_deste_segmento.extend(gerar_sequencia_datas(contexto_ano, contexto_mes, dia_start, mes_dest, dia_end))
                                contexto_mes = mes_dest; i += 4; continue

                    # Data Simples ou Composta (17 ou 17/18)
                    if "/" in tok: 
                        partes = tok.split("/")
                        dt = criar_data_segura(contexto_ano, contexto_mes, int(partes[0]))
                        if dt: datas_deste_segmento.append(dt)
                        # Se não for complexo e não tiver offset, adiciona o segundo dia também
                        if offset_dias == 0 and not is_complex: 
                             dt2 = criar_data_segura(contexto_ano, contexto_mes, int(partes[1]))
                             if dt2: datas_deste_segmento.append(dt2)
                        i += 1; continue
                    else:
                        dt = criar_data_segura(contexto_ano, contexto_mes, int(tok))
                        if dt: datas_deste_segmento.append(dt)
                        i += 1; continue
                i += 1
            
        elif "DLY" in segmento or "DAILY" in segmento:
            # DLY explícito sem datas -> B até C
            curr = dt_b
            while curr <= dt_c: datas_deste_segmento.append(curr); curr += timedelta(days=1)
            achou_nova_definicao = True

        # --- ATUALIZAÇÃO DE CONTEXTO ---
        if achou_nova_definicao:
            ultima_lista_datas = datas_deste_segmento
            ultimo_filtro_semana = filtro_semana_deste_segmento
        else:
            # Herança: Segmento só tem horário, usa datas/dias do anterior
            datas_deste_segmento = ultima_lista_datas
            filtro_semana_deste_segmento = ultimo_filtro_semana

        # --- GERAÇÃO FINAL DE SLOTS ---
        # Se não tem datas definidas, assume intervalo B->C (fallback DLY)
        lista_final = datas_deste_segmento if datas_deste_segmento else []
        if not lista_final and not achou_nova_definicao and not ultimo_filtro_semana:
             # Caso extremo: DLY implícito desde o início
             curr = dt_b
             while curr <= dt_c: lista_final.append(curr); curr += timedelta(days=1)

        for dt_crua in lista_final:
            dt_final = ajustar_ano_referencia(dt_crua, dt_b)
            if not dt_final: continue

            # Filtro de Dia da Semana
            if is_complex and filtro_dia_inicio is not None:
                if dt_final.weekday() != filtro_dia_inicio: continue
            elif filtro_semana_deste_segmento and dt_final.weekday() not in filtro_semana_deste_segmento:
                continue
            
            # Montagem do Slot
            s_ini = dt_final.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
            s_fim = s_ini + timedelta(days=offset_dias)
            s_fim = s_fim.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
            
            # Correção para fim menor que início (overnight dentro do mesmo dia base corrigido)
            if s_fim < s_ini: s_fim += timedelta(days=1)
            
            # Filtro de Validade Absoluta (B e C)
            if s_fim < dt_b or s_ini > dt_c: continue
            
            slots.append({'inicio': s_ini, 'fim': s_fim})

    # Ordenação e Retorno
    slots.sort(key=lambda x: x['inicio'])
    return slots