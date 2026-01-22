import re
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES ---
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
    try:
        if not date_str: return None
        clean_str = str(date_str).replace("-", "").replace(":", "").replace(" ", "").strip()
        if len(clean_str) == 10:
            return datetime.strptime(clean_str, "%y%m%d%H%M")
        elif len(clean_str) == 12:
            return datetime.strptime(clean_str, "%Y%m%d%H%M")
        return None
    except: return None

def criar_data_segura(ano, mes, dia):
    try:
        return datetime(ano, mes, dia)
    except: return None

def gerar_sequencia_datas(ano_base, mes_ini, dia_ini, mes_fim, dia_fim):
    datas = []
    dt_start = criar_data_segura(ano_base, mes_ini, dia_ini)
    dt_end = criar_data_segura(ano_base, mes_fim, dia_fim)
    
    if not dt_start or not dt_end: return []
    
    # Ajuste simples de virada de ano no range
    if dt_end < dt_start:
        dt_end = dt_end.replace(year=ano_base + 1)
        
    curr = dt_start
    while curr <= dt_end:
        datas.append(curr)
        curr += timedelta(days=1)
    return datas

def ajustar_ano_referencia(dt, dt_referencia_b):
    if not dt: return None
    if dt.month < dt_referencia_b.month and dt_referencia_b.month > 10:
        return dt.replace(year=dt_referencia_b.year + 1)
    return dt

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    V7: Suporte Total a Ranges (Dias do Mês e Dias da Semana).
    """
    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    if not dt_b or not dt_c: return []

    slots = []
    text = item_d_text.upper().strip()
    
    re_horario = re.compile(r'(\d{4})-(\d{4})')
    matches = list(re_horario.finditer(text))
    
    last_end = 0
    contexto_ano = dt_b.year
    contexto_mes = dt_b.month 

    if not matches:
        return [{'inicio': dt_b, 'fim': dt_c}]

    for match in matches:
        h_ini_str, h_fim_str = match.groups()
        segmento = text[last_end:match.start()]
        last_end = match.end()
        
        if "DLY" in segmento or "DAILY" in segmento:
            curr = dt_b
            while curr <= dt_c:
                s_ini = curr.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
                s_fim = curr.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
                if s_fim < s_ini: s_fim += timedelta(days=1)
                if s_fim >= dt_b and s_ini <= dt_c:
                    slots.append({'inicio': s_ini, 'fim': s_fim})
                curr += timedelta(days=1)
        
        else:
            tokens = re.findall(r'[A-Za-z]+|\d+', segmento)
            
            # --- 1. SCANNER DE DIAS DA SEMANA (COM RANGES) ---
            dias_permitidos = set()
            k = 0
            while k < len(tokens):
                tok = tokens[k]
                if tok in WEEK_MAP:
                    # Verifica se é Range: [DIA] [TIL] [DIA]
                    if k + 2 < len(tokens) and tokens[k+1] == "TIL" and tokens[k+2] in WEEK_MAP:
                        idx_start = WEEK_MAP[tok]
                        idx_end = WEEK_MAP[tokens[k+2]]
                        
                        if idx_start <= idx_end:
                            dias_permitidos.update(range(idx_start, idx_end + 1))
                        else:
                            # Range circular (ex: FRI TIL MON -> Sex, Sab, Dom, Seg)
                            dias_permitidos.update(range(idx_start, 7))
                            dias_permitidos.update(range(0, idx_end + 1))
                        k += 3 # Pula os 3 tokens usados
                    else:
                        # Dia único
                        dias_permitidos.add(WEEK_MAP[tok])
                        k += 1
                else:
                    k += 1
            
            # --- 2. SCANNER DE DATAS ---
            i = 0
            datas_candidatas = []
            
            while i < len(tokens):
                tok = tokens[i]
                
                if tok in MONTH_MAP:
                    contexto_mes = MONTH_MAP[tok]
                    i += 1
                    continue
                
                # Ignora tokens de semana já processados
                if tok in WEEK_MAP or (tok == "TIL" and i>0 and tokens[i-1] in WEEK_MAP):
                    i += 1
                    continue

                if tok.isdigit():
                    dia_start = int(tok)
                    
                    if i + 2 < len(tokens) and tokens[i+1] == "TIL":
                        alvo = tokens[i+2]
                        if alvo.isdigit(): # Range Simples
                            dia_end = int(alvo)
                            lista_dt = gerar_sequencia_datas(contexto_ano, contexto_mes, dia_start, contexto_mes, dia_end)
                            datas_candidatas.extend(lista_dt)
                            i += 3
                            continue
                        elif alvo in MONTH_MAP: # Range Multi-Mês
                            mes_dest = MONTH_MAP[alvo]
                            if i + 3 < len(tokens) and tokens[i+3].isdigit():
                                dia_dest = int(tokens[i+3])
                                lista_dt = gerar_sequencia_datas(contexto_ano, contexto_mes, dia_start, mes_dest, dia_dest)
                                datas_candidatas.extend(lista_dt)
                                contexto_mes = mes_dest
                                i += 4
                                continue

                    # Single
                    dt = criar_data_segura(contexto_ano, contexto_mes, dia_start)
                    if dt: datas_candidatas.append(dt)
                    i += 1
                    continue
                
                i += 1

            # --- 3. GERAÇÃO DE SLOTS ---
            for dt_crua in datas_candidatas:
                dt_final = ajustar_ano_referencia(dt_crua, dt_b)
                if not dt_final: continue

                if dias_permitidos and dt_final.weekday() not in dias_permitidos:
                    continue
                
                s_ini = dt_final.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
                s_fim = dt_final.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
                if s_fim < s_ini: s_fim += timedelta(days=1)
                
                slots.append({'inicio': s_ini, 'fim': s_fim})

    return slots