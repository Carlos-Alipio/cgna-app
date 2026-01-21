import re
from datetime import datetime, timedelta

def parse_notam_date(date_str):
    try:
        if not date_str or len(str(date_str)) != 10: return None
        return datetime.strptime(str(date_str), "%y%m%d%H%M")
    except: return None

def calculate_sun_times(date_obj):
    """Horários fixos para teste"""
    sr = date_obj.replace(hour=9, minute=0, second=0)
    ss = date_obj.replace(hour=21, minute=0, second=0)
    return sr, ss

def extrair_horarios(texto_horario, base_date):
    """Lê strings de hora: '1000-1500', 'SR-SS'"""
    slots = []
    texto_clean = texto_horario.upper().replace("/", "-").replace(" TO ", "-").strip()
    partes = re.split(r'\s+AND\s+|\s+', texto_clean)
    sr_dt, ss_dt = calculate_sun_times(base_date)

    for parte in partes:
        if "-" not in parte: continue
        try:
            inicio_str, fim_str = parte.split("-")
            
            if "SR" in inicio_str: dt_ini = sr_dt
            elif "SS" in inicio_str: dt_ini = ss_dt
            elif re.match(r'^\d{4}$', inicio_str):
                dt_ini = base_date.replace(hour=int(inicio_str[:2]), minute=int(inicio_str[2:]))
            else: continue

            if "SR" in fim_str: dt_fim = sr_dt
            elif "SS" in fim_str: dt_fim = ss_dt
            elif re.match(r'^\d{4}$', fim_str):
                dt_fim = base_date.replace(hour=int(fim_str[:2]), minute=int(fim_str[2:]))
                if dt_fim < dt_ini: dt_fim += timedelta(days=1)
            else: continue

            slots.append({'inicio': dt_ini, 'fim': dt_fim})
        except: continue
    return slots

def processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao):
    """
    ESTRATÉGIA 'DIVIDIR PARA CONQUISTAR':
    1. Encontra todos os horários (ex: 0400-0759).
    2. Usa o horário como delimitador para fatiar o texto em blocos.
    3. Analisa o texto À ESQUERDA do horário para achar as datas.
    """
    week_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}
    resultado = []
    
    # Regex para achar horários (HHMM-HHMM ou SR-SS)
    # Grupo 1 pega o horário completo
    pattern_time = r'(\d{4}-\d{4}|SR-SS|SR-\d{4}|\d{4}-SS)'
    
    matches = list(re.finditer(pattern_time, text))
    if not matches: return []

    last_end = 0
    
    for match in matches:
        horario_str = match.group(1)
        end_pos = match.end()
        
        # Pega o texto desde o fim do último horário até o horário atual
        # Ex: "JAN 10 TIL 16 TUE WED " (antes de chegar no 0400-0759)
        segmento = text[last_end:match.start()].strip()
        last_end = end_pos # Atualiza para o próximo loop
        
        if not segmento: continue

        # --- ANÁLISE DO SEGMENTO ---
        
        # 1. Identifica e remove Dias da Semana (Filtros)
        dias_filtro = set()
        segmento_limpo = segmento
        for dia, idx in week_map.items():
            if dia in segmento_limpo:
                dias_filtro.add(idx)
                segmento_limpo = segmento_limpo.replace(dia, "") # Remove para sobrar só a data
        
        segmento_limpo = segmento_limpo.strip()
        
        # 2. Interpreta Datas (Ranges ou Únicas) no que sobrou
        # Padroes: "JAN 10 TIL 16" ou "JAN 10 TIL JAN 26" ou "JAN 10"
        
        ini_dt = None
        fim_dt = None
        
        # Regex A: Range com Mês explícito no fim (JAN 10 TIL JAN 26)
        match_full = re.search(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+([A-Z]{3})\s+(\d{1,2})', segmento_limpo)
        
        # Regex B: Range com Mês implícito (JAN 10 TIL 16)
        match_partial = re.search(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+(\d{1,2})', segmento_limpo)
        
        # Regex C: Data Única (JAN 10) - Caso não tenha TIL
        match_single = re.search(r'([A-Z]{3})\s+(\d{1,2})$', segmento_limpo)
        
        y = dt_b.year
        
        try:
            if match_full:
                m1, d1, m2, d2 = match_full.groups()
                ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                fim_dt = datetime.strptime(f"{y} {m2} {d2}", "%Y %b %d")
            elif match_partial:
                m1, d1, d2 = match_partial.groups()
                ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                fim_dt = datetime.strptime(f"{y} {m1} {d2}", "%Y %b %d")
            elif match_single and "TIL" not in segmento_limpo:
                m1, d1 = match_single.groups()
                ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                fim_dt = ini_dt # Data única, inicio = fim

            if ini_dt and fim_dt:
                # Ajuste de ano
                if fim_dt < ini_dt: fim_dt = fim_dt.replace(year=y+1)
                
                # Gera dias
                curr = ini_dt
                while curr <= fim_dt:
                    # Aplica filtro de dia da semana (se houver)
                    if not dias_filtro or curr.weekday() in dias_filtro:
                        slots = extrair_horarios(horario_str, curr) # Usa o horário que cortamos
                        resultado.extend(slots)
                    curr += timedelta(days=1)
        except:
            pass

    return resultado

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    Função Mestre
    """
    if not item_d_text or not item_d_text.strip(): return []

    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    if not dt_b or not dt_c: return []

    # 1. Limpeza Básica
    text = item_d_text.upper().strip()
    text = text.replace('\n', ' ').replace(',', ' ').replace('.', ' ').replace('  ', ' ')
    
    # Limpa barras de datas (07/08 -> 07, MON/TUE -> MON)
    text = re.sub(r'(\d{1,2})/\d{1,2}', r'\1', text)
    days_pattern = r'(MON|TUE|WED|THU|FRI|SAT|SUN)/(MON|TUE|WED|THU|FRI|SAT|SUN)'
    text = re.sub(days_pattern, r'\1', text)

    # ==========================================================================
    # ESTRATÉGIA PRIORITÁRIA: SEGMENTAÇÃO POR HORÁRIO (Resolve SBGR e Complexos)
    # Se houver horários no formato 0000-0000, tentamos fatiar a string.
    # ==========================================================================
    if re.search(r'\d{4}-\d{4}', text):
        res_complexo = processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao)
        if res_complexo:
            return res_complexo

    # ==========================================================================
    # FALLBACKS (Para casos simples como DLY ou MON TIL FRI sem horários complexos)
    # ==========================================================================
    
    # CASO: DLY
    if "DLY" in text or "DAILY" in text:
        horarios_str = text.replace("DLY", "").replace("DAILY", "").strip()
        dias_exc = []
        if "EXC" in horarios_str:
            parts = horarios_str.split("EXC")
            horarios_str = parts[0].strip()
            exc_text = parts[1].strip()
            week_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}
            for k, v in week_map.items():
                if k in exc_text: dias_exc.append(v)
        
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() in dias_exc:
                curr += timedelta(days=1)
                continue
            slots = extrair_horarios(horarios_str, curr)
            resultado_final = [] # Bugfix var name
            resultado_final.extend(slots) # Bugfix var name
            # Se usarmos o loop acima, precisamos acumular numa lista
            # Como DLY é regra unica, podemos retornar direto da logica extraida
            # Mas vamos manter coerencia.
        
        # Re-implementação rápida correta do DLY para não quebrar:
        res_dly = []
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() not in dias_exc:
                res_dly.extend(extrair_horarios(horarios_str, curr))
            curr += timedelta(days=1)
        return res_dly

    # CASO: MON TIL FRI (Intervalo Semanal)
    week_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}
    match_week_range = re.search(r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)', text)
    if match_week_range:
        start_idx = week_map[match_week_range.group(1)]
        end_idx = week_map[match_week_range.group(2)]
        if start_idx <= end_idx: validos = list(range(start_idx, end_idx + 1))
        else: validos = list(range(start_idx, 7)) + list(range(0, end_idx + 1))
        horario = text.replace(match_week_range.group(0), "").strip()
        
        res_week = []
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() in validos:
                res_week.extend(extrair_horarios(horario, curr))
            curr += timedelta(days=1)
        return res_week

    # CASO: Dias Soltos (MON WED FRI)
    if any(d in text for d in week_map.keys()) and "TIL" not in text:
        alvo = {week_map[d] for d in week_map if d in text}
        horario = text
        for d in week_map: horario = horario.replace(d, "")
        
        res_days = []
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() in alvo:
                res_days.extend(extrair_horarios(horario, curr))
            curr += timedelta(days=1)
        return res_days

    return []

# ==============================================================================