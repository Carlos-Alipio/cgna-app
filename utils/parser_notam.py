import re
from datetime import datetime, timedelta

# Mapa de meses
MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    "FEV": 2, "ABR": 4, "MAI": 5, "AGO": 8, "SET": 9, "OUT": 10, "DEZ": 12
}

def parse_notam_date(date_str):
    try:
        if not date_str: return None
        clean_str = str(date_str).replace("-", "").replace(":", "").replace(" ", "").strip()
        if len(clean_str) == 10:
            return datetime.strptime(clean_str, "%y%m%d%H%M")
        elif len(clean_str) == 12:
            return datetime.strptime(clean_str, "%Y%m%d%H%M")
        return None
    except: return None

def ajustar_ano_data(dia, mes, dt_referencia):
    ano = dt_referencia.year
    try:
        dt_criada = datetime(ano, mes, dia)
        # Ajuste de virada de ano (ex: Dezembro -> Janeiro)
        if dt_criada.month < dt_referencia.month and dt_referencia.month > 10:
             dt_criada = dt_criada.replace(year=ano + 1)
        return dt_criada
    except: return None

def tokenize_segment(text):
    """
    Quebra o texto em tokens limpos, preservando / e separando TIL.
    Ex: "FEB 03 TIL 11" -> ["FEB", "03", "TIL", "11"]
    Ex: "DEC 01/02" -> ["DEC", "01/02"]
    """
    # Adiciona espaços ao redor de palavras-chave para garantir separação
    clean = text.replace(" TIL ", " TIL ").replace(" TO ", " TIL ")
    # Normaliza espaços
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean.split(' ')

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    V4: Tokenizer Lookahead. Robustez total para Ranges e Listas.
    """
    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    if not dt_b or not dt_c: return []

    slots = []
    text = item_d_text.upper().strip()
    
    # Identifica horários (HHMM-HHMM)
    re_horario = re.compile(r'(\d{4})-(\d{4})')
    matches = list(re_horario.finditer(text))
    
    last_end = 0
    contexto_mes = dt_b.month # Mês inicial (default)

    if not matches:
        return [{'inicio': dt_b, 'fim': dt_c}]

    for match in matches:
        h_ini_str, h_fim_str = match.groups()
        
        # Segmento de texto ANTES do horário atual
        segmento = text[last_end:match.start()].strip()
        last_end = match.end()
        
        # --- CASO 1: DLY ---
        if "DLY" in segmento or "DAILY" in segmento:
            curr = dt_b
            while curr <= dt_c:
                s_ini = curr.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
                s_fim = curr.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
                if s_fim < s_ini: s_fim += timedelta(days=1)
                
                if s_fim >= dt_b and s_ini <= dt_c:
                    slots.append({'inicio': s_ini, 'fim': s_fim})
                curr += timedelta(days=1)
        
        # --- CASO 2: PROCESSAMENTO POR TOKENS ---
        else:
            tokens = tokenize_segment(segmento)
            i = 0
            datas_base = []
            
            while i < len(tokens):
                tok = tokens[i]
                
                # A) É um Mês? (Atualiza contexto)
                if tok in MONTH_MAP:
                    contexto_mes = MONTH_MAP[tok]
                    i += 1
                    continue
                
                # B) É uma Data Composta? (01/02)
                if "/" in tok and re.match(r'\d+/\d+', tok):
                    try:
                        p1, p2 = tok.split("/")
                        dia1 = int(p1)
                        dia2 = int(p2)
                        
                        # Verifica se é o caso de Evento Único (DEC 01/02 2133-0115)
                        # Regra: Se cruza meia-noite (h_fim < h_ini), gera só o dia 1.
                        cruza_noite = int(h_fim_str) < int(h_ini_str)
                        
                        dt1 = ajustar_ano_data(dia1, contexto_mes, dt_b)
                        if dt1: datas_base.append(dt1)
                        
                        if not cruza_noite:
                             dt2 = ajustar_ano_data(dia2, contexto_mes, dt_b)
                             if dt2: datas_base.append(dt2)
                    except: pass
                    i += 1
                    continue

                # C) É um Número? (Pode ser Single ou Início de Range)
                if tok.isdigit():
                    dia_start = int(tok)
                    
                    # Lookahead: O próximo token é TIL?
                    if (i + 2 < len(tokens)) and (tokens[i+1] == "TIL") and (tokens[i+2].isdigit()):
                        # É UM RANGE (Start TIL End)
                        dia_end = int(tokens[i+2])
                        
                        # Gera lista de dias
                        if dia_end >= dia_start:
                            rng = range(dia_start, dia_end + 1)
                        else:
                            rng = [dia_start, dia_end] # Fallback
                            
                        for d in rng:
                            dt = ajustar_ano_data(d, contexto_mes, dt_b)
                            if dt: datas_base.append(dt)
                        
                        i += 3 # Pula [NUM, TIL, NUM]
                        continue
                    else:
                        # É UM SINGLE
                        dt = ajustar_ano_data(dia_start, contexto_mes, dt_b)
                        if dt: datas_base.append(dt)
                        i += 1
                        continue
                
                # Token não reconhecido, avança
                i += 1

            # Gera slots para todas as datas encontradas
            for dt_base in datas_base:
                s_ini = dt_base.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
                s_fim = dt_base.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
                if s_fim < s_ini: s_fim += timedelta(days=1)
                
                slots.append({'inicio': s_ini, 'fim': s_fim})

    return slots