import re
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES ---
MAX_DAYS_PROJECT = 90

# Regex pré-compiladas
RE_HORARIO_SEGMENT = re.compile(r'(\d{4}-\d{4}|SR-SS|SR-\d{4}|\d{4}-SS)')
RE_BARRA_DATA = re.compile(r'(\d{1,2})/\d{1,2}')
RE_BARRA_DIA = re.compile(r'(MON|TUE|WED|THU|FRI|SAT|SUN)/(MON|TUE|WED|THU|FRI|SAT|SUN)')
RE_FULL_RANGE = re.compile(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+([A-Z]{3})\s+(\d{1,2})')
RE_PARTIAL_RANGE = re.compile(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+(\d{1,2})')
RE_SINGLE_DATE = re.compile(r'([A-Z]{3})\s+(\d{1,2})$')

MONTHS_LIST = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

def parse_notam_date(date_str):
    try:
        if not date_str or len(str(date_str)) != 10: return None
        return datetime.strptime(str(date_str), "%y%m%d%H%M")
    except: return None

def calculate_sun_times(date_obj):
    sr = date_obj.replace(hour=9, minute=0, second=0)
    ss = date_obj.replace(hour=21, minute=0, second=0)
    return sr, ss

def extrair_horarios(texto_horario, base_date):
    slots = []
    texto_clean = texto_horario.upper().replace("/", "-").replace(" TO ", "-").strip()
    partes = texto_clean.replace(" AND ", " ").split(" ")
    sr_dt, ss_dt = calculate_sun_times(base_date)

    for parte in partes:
        if "-" not in parte: continue
        try:
            inicio_str, fim_str = parte.split("-")
            
            if "SR" in inicio_str: dt_ini = sr_dt
            elif "SS" in inicio_str: dt_ini = ss_dt
            elif len(inicio_str) == 4 and inicio_str.isdigit():
                dt_ini = base_date.replace(hour=int(inicio_str[:2]), minute=int(inicio_str[2:]))
            else: continue

            if "SR" in fim_str: dt_fim = sr_dt
            elif "SS" in fim_str: dt_fim = ss_dt
            elif len(fim_str) == 4 and fim_str.isdigit():
                dt_fim = base_date.replace(hour=int(fim_str[:2]), minute=int(fim_str[2:]))
                if dt_fim < dt_ini: dt_fim += timedelta(days=1)
            else: continue

            slots.append({'inicio': dt_ini, 'fim': dt_fim})
        except: continue
    return slots

def ajustar_ano(dt_alvo, dt_inicio_vigencia):
    """
    Se a data lida for muito anterior à data de início da vigência (B),
    assume que é do ano seguinte.
    Ex: Item B = DEC 2025. Data lida = JAN 01 (assume 2025).
    JAN < DEC -> Corrige para JAN 2026.
    """
    # Se o mês alvo é menor que o mês de início (Ex: Jan < Dec)
    # E o ano é o mesmo, soma 1 ano.
    if dt_alvo.month < dt_inicio_vigencia.month and dt_alvo.year == dt_inicio_vigencia.year:
        return dt_alvo.replace(year=dt_alvo.year + 1)
    
    # Caso extra: Se a data for menor que o inicio, mas no mesmo mês/ano (ex: dia 01 vs dia 19)
    # Geralmente mantemos, pois pode ser erro de digitação, 
    # mas o parser vai filtrar depois se estiver fora da vigência.
    return dt_alvo

def processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao):
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

        # 1. Filtro Dias da Semana
        dias_filtro = set()
        if any(d in segmento for d in week_map):
            for dia, idx in week_map.items():
                if dia in segmento:
                    dias_filtro.add(idx)
                    segmento = segmento.replace(dia, "") 
        
        segmento_limpo = segmento.strip()
        processed_segment = False

        # 2. Tenta Ranges (TIL)
        ini_dt, fim_dt = None, None
        m_full = RE_FULL_RANGE.search(segmento_limpo)
        m_part = RE_PARTIAL_RANGE.search(segmento_limpo)
        m_single = RE_SINGLE_DATE.search(segmento_limpo) # JAN 10 (Sem TIL)

        if m_full or m_part:
            processed_segment = True
            try:
                if m_full:
                    m1, d1, m2, d2 = m_full.groups()
                    ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                    fim_dt = datetime.strptime(f"{y} {m2} {d2}", "%Y %b %d")
                elif m_part:
                    m1, d1, d2 = m_part.groups()
                    ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                    fim_dt = datetime.strptime(f"{y} {m1} {d2}", "%Y %b %d")

                if ini_dt and fim_dt:
                    # CORREÇÃO DE ANO
                    ini_dt = ajustar_ano(ini_dt, dt_b)
                    # O fim deve ser checado em relação ao início corrigido
                    if fim_dt.month < ini_dt.month: 
                        fim_dt = fim_dt.replace(year=ini_dt.year + 1)
                    else:
                        fim_dt = fim_dt.replace(year=ini_dt.year)

                    if (fim_dt - ini_dt).days > MAX_DAYS_PROJECT:
                        fim_dt = ini_dt + timedelta(days=MAX_DAYS_PROJECT)

                    curr = ini_dt
                    while curr <= fim_dt:
                        if not dias_filtro or curr.weekday() in dias_filtro:
                            resultado.extend(extrair_horarios(horario_str, curr))
                        curr += timedelta(days=1)
            except: pass
        
        # 3. Lista de Datas (JAN 05 08...)
        if not processed_segment:
            found_months = []
            for mon in MONTHS_LIST:
                idx = segmento_limpo.find(mon)
                if idx != -1: found_months.append((idx, mon))
            
            found_months.sort()
            
            if found_months:
                processed_segment = True
                for i, (idx, mon) in enumerate(found_months):
                    start_slice = idx + len(mon)
                    end_slice = found_months[i+1][0] if i + 1 < len(found_months) else len(segmento_limpo)
                    nums_str = segmento_limpo[start_slice:end_slice]
                    
                    dias_list = []
                    for token in nums_str.replace(",", " ").split():
                        if token.isdigit() and len(token) <= 2:
                            dias_list.append(int(token))
                    
                    try:
                        mes_obj = datetime.strptime(mon, "%b")
                        for d in dias_list:
                            dt_base = datetime(y, mes_obj.month, d)
                            
                            # CORREÇÃO DE ANO
                            dt_base = ajustar_ano(dt_base, dt_b)
                            
                            if not dias_filtro or dt_base.weekday() in dias_filtro:
                                resultado.extend(extrair_horarios(horario_str, dt_base))
                    except: pass
            
            # 4. Caso Sobra (Só números, assume mês do B)
            else:
                tokens = segmento_limpo.split()
                if all(t.isdigit() for t in tokens) and len(tokens) > 0:
                    try:
                        for t in tokens:
                            dt_base = datetime(y, dt_b.month, int(t))
                            dt_base = ajustar_ano(dt_base, dt_b) # Aplica correção aqui tb
                            if not dias_filtro or dt_base.weekday() in dias_filtro:
                                resultado.extend(extrair_horarios(horario_str, dt_base))
                    except: pass

    # Filtro Final: Remove datas fora da vigência global (B e C)
    resultado_final = [r for r in resultado if dt_b <= r['inicio'] <= dt_c + timedelta(days=1)]
    return resultado_final

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    if not item_d_text or not item_d_text.strip(): return []

    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    if not dt_b or not dt_c: return []

    if (dt_c - dt_b).days > MAX_DAYS_PROJECT:
        dt_c = dt_b + timedelta(days=MAX_DAYS_PROJECT)

    text = item_d_text.upper().strip()
    text = text.replace('\n', ' ').replace(',', ' ').replace('.', ' ').replace('  ', ' ')
    text = RE_BARRA_DATA.sub(r'\1', text)
    text = RE_BARRA_DIA.sub(r'\1', text)
    text = text.replace(u'\xa0', u' ')

    if RE_HORARIO_SEGMENT.search(text):
        res = processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao)
        if res: return res

    # FALLBACKS SIMPLES (DLY, WEEK, ETC)
    week_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}

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

    m_week = re.search(r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)', text)
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