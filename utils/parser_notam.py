import re
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DE PERFORMANCE ---
MAX_DAYS_PROJECT = 90  # Trava de segurança: processa no máx 90 dias

# Regex pré-compiladas para velocidade
RE_HORARIO_SEGMENT = re.compile(r'(\d{4}-\d{4}|SR-SS|SR-\d{4}|\d{4}-SS)')
RE_BARRA_DATA = re.compile(r'(\d{1,2})/\d{1,2}')
RE_BARRA_DIA = re.compile(r'(MON|TUE|WED|THU|FRI|SAT|SUN)/(MON|TUE|WED|THU|FRI|SAT|SUN)')
RE_FULL_RANGE = re.compile(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+([A-Z]{3})\s+(\d{1,2})')
RE_PARTIAL_RANGE = re.compile(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+(\d{1,2})')
RE_SINGLE_DATE = re.compile(r'([A-Z]{3})\s+(\d{1,2})$')
RE_WEEK_RANGE = re.compile(r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)')

def parse_notam_date(date_str):
    try:
        if not date_str or len(str(date_str)) != 10: return None
        return datetime.strptime(str(date_str), "%y%m%d%H%M")
    except: return None

def calculate_sun_times(date_obj):
    # Valores fixos para performance (evita bibliotecas pesadas)
    sr = date_obj.replace(hour=9, minute=0, second=0)
    ss = date_obj.replace(hour=21, minute=0, second=0)
    return sr, ss

def extrair_horarios(texto_horario, base_date):
    slots = []
    # Limpeza rápida
    texto_clean = texto_horario.upper().replace("/", "-").replace(" TO ", "-").strip()
    
    # Split manual simples é mais rápido que regex complexa aqui
    partes = texto_clean.replace(" AND ", " ").split(" ")
    
    sr_dt, ss_dt = calculate_sun_times(base_date)

    for parte in partes:
        if "-" not in parte: continue
        try:
            inicio_str, fim_str = parte.split("-")
            
            # Resolução Rápida de Início
            if inicio_str == "SR": dt_ini = sr_dt
            elif inicio_str == "SS": dt_ini = ss_dt
            elif len(inicio_str) == 4 and inicio_str.isdigit():
                dt_ini = base_date.replace(hour=int(inicio_str[:2]), minute=int(inicio_str[2:]))
            else: continue

            # Resolução Rápida de Fim
            if fim_str == "SR": dt_fim = sr_dt
            elif fim_str == "SS": dt_fim = ss_dt
            elif len(fim_str) == 4 and fim_str.isdigit():
                dt_fim = base_date.replace(hour=int(fim_str[:2]), minute=int(fim_str[2:]))
                if dt_fim < dt_ini: dt_fim += timedelta(days=1)
            else: continue

            slots.append({'inicio': dt_ini, 'fim': dt_fim})
        except: continue
    return slots

def processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao):
    """Segmentação otimizada para performance"""
    week_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}
    resultado = []
    
    matches = list(RE_HORARIO_SEGMENT.finditer(text))
    if not matches: return []

    last_end = 0
    y = dt_b.year

    for match in matches:
        horario_str = match.group(1)
        segmento = text[last_end:match.start()].strip()
        last_end = match.end()
        
        if not segmento: continue

        # 1. Extração rápida de filtro de dias
        dias_filtro = set()
        # Verificação rápida se existe dia da semana na string antes de iterar
        if any(d in segmento for d in week_map):
            for dia, idx in week_map.items():
                if dia in segmento:
                    dias_filtro.add(idx)
                    segmento = segmento.replace(dia, "") 
        
        segmento_limpo = segmento.strip()
        
        # 2. Match de Datas (Prioridade: Full -> Partial -> Single)
        ini_dt, fim_dt = None, None
        
        m_full = RE_FULL_RANGE.search(segmento_limpo)
        if m_full:
            m1, d1, m2, d2 = m_full.groups()
            try:
                ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                fim_dt = datetime.strptime(f"{y} {m2} {d2}", "%Y %b %d")
            except: pass
        else:
            m_part = RE_PARTIAL_RANGE.search(segmento_limpo)
            if m_part:
                m1, d1, d2 = m_part.groups()
                try:
                    ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                    fim_dt = datetime.strptime(f"{y} {m1} {d2}", "%Y %b %d")
                except: pass
            else:
                m_single = RE_SINGLE_DATE.search(segmento_limpo)
                if m_single and "TIL" not in segmento_limpo:
                    m1, d1 = m_single.groups()
                    try:
                        ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                        fim_dt = ini_dt
                    except: pass

        if ini_dt and fim_dt:
            if fim_dt < ini_dt: fim_dt = fim_dt.replace(year=y+1)
            
            # --- OTIMIZAÇÃO CRÍTICA: CAP NO INTERVALO ---
            # Se o intervalo for maior que o limite, corta.
            delta_days = (fim_dt - ini_dt).days
            if delta_days > MAX_DAYS_PROJECT:
                fim_dt = ini_dt + timedelta(days=MAX_DAYS_PROJECT)

            # Loop de geração
            curr = ini_dt
            while curr <= fim_dt:
                if not dias_filtro or curr.weekday() in dias_filtro:
                    slots = extrair_horarios(horario_str, curr)
                    resultado.extend(slots)
                curr += timedelta(days=1)

    return resultado

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """Função Mestre Otimizada"""
    if not item_d_text or not item_d_text.strip(): return []

    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    if not dt_b or not dt_c: return []

    # TRAVA DE SEGURANÇA GERAL: Se o NOTAM tem validade > 90 dias, cortamos dt_c
    if (dt_c - dt_b).days > MAX_DAYS_PROJECT:
        dt_c = dt_b + timedelta(days=MAX_DAYS_PROJECT)

    # Limpeza
    text = item_d_text.upper().strip()
    text = text.replace('\n', ' ').replace(',', ' ').replace('.', ' ').replace('  ', ' ')
    
    # Regex pré-compilada é mais rápida
    text = RE_BARRA_DATA.sub(r'\1', text)
    text = RE_BARRA_DIA.sub(r'\1', text)

    # 1. TENTA SEGMENTAÇÃO (Mais robusto)
    if RE_HORARIO_SEGMENT.search(text):
        res = processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao)
        if res: return res

    # 2. FALLBACKS RÁPIDOS
    week_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}

    # DLY
    if "DLY" in text or "DAILY" in text:
        horarios_str = text.replace("DLY", "").replace("DAILY", "").strip()
        dias_exc = set()
        if "EXC" in horarios_str:
            parts = horarios_str.split("EXC")
            horarios_str = parts[0].strip()
            exc_text = parts[1].strip()
            for k, v in week_map.items():
                if k in exc_text: dias_exc.add(v)
        
        res_dly = []
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() not in dias_exc:
                res_dly.extend(extrair_horarios(horarios_str, curr))
            curr += timedelta(days=1)
        return res_dly

    # MON TIL FRI
    m_week = RE_WEEK_RANGE.search(text)
    if m_week:
        start, end = week_map[m_week.group(1)], week_map[m_week.group(2)]
        validos = set(range(start, end + 1)) if start <= end else set(list(range(start, 7)) + list(range(0, end + 1)))
        horario = text.replace(m_week.group(0), "").strip()
        
        res_week = []
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() in validos:
                res_week.extend(extrair_horarios(horario, curr))
            curr += timedelta(days=1)
        return res_week

    # MON WED FRI
    if any(d in text for d in week_map):
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