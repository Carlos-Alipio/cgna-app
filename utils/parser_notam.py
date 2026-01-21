import re
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DE PERFORMANCE ---
MAX_DAYS_PROJECT = 90

# Regex pré-compiladas
RE_HORARIO_SEGMENT = re.compile(r'(\d{4}-\d{4}|SR-SS|SR-\d{4}|\d{4}-SS)')
RE_BARRA_DATA = re.compile(r'(\d{1,2})/\d{1,2}')
RE_BARRA_DIA = re.compile(r'(MON|TUE|WED|THU|FRI|SAT|SUN)/(MON|TUE|WED|THU|FRI|SAT|SUN)')
RE_FULL_RANGE = re.compile(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+([A-Z]{3})\s+(\d{1,2})')
RE_PARTIAL_RANGE = re.compile(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+(\d{1,2})')
RE_SINGLE_DATE = re.compile(r'([A-Z]{3})\s+(\d{1,2})$')

# Lista de meses para iteração rápida
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

        # 1. Filtro de Dias da Semana
        dias_filtro = set()
        if any(d in segmento for d in week_map):
            for dia, idx in week_map.items():
                if dia in segmento:
                    dias_filtro.add(idx)
                    segmento = segmento.replace(dia, "") 
        
        segmento_limpo = segmento.strip()
        # Se o segmento ficou vazio (ex: "MON TUE 1000-1200"), assume intervalo completo
        # Mas cuidado, pode ser continuação de lista anterior.
        
        processed_segment = False

        # 2. Tenta Ranges (TIL) - Prioridade Alta
        ini_dt, fim_dt = None, None
        m_full = RE_FULL_RANGE.search(segmento_limpo)
        m_part = RE_PARTIAL_RANGE.search(segmento_limpo)

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
                    if fim_dt < ini_dt: fim_dt = fim_dt.replace(year=y+1)
                    if (fim_dt - ini_dt).days > MAX_DAYS_PROJECT:
                        fim_dt = ini_dt + timedelta(days=MAX_DAYS_PROJECT)

                    curr = ini_dt
                    while curr <= fim_dt:
                        if not dias_filtro or curr.weekday() in dias_filtro:
                            resultado.extend(extrair_horarios(horario_str, curr))
                        curr += timedelta(days=1)
            except: pass
        
        # 3. Se não achou TIL, tenta LISTA DE DATAS (JAN 05 08 10)
        if not processed_segment:
            # Procura ocorrências de meses no segmento
            found_months = []
            for mon in MONTHS_LIST:
                idx = segmento_limpo.find(mon)
                if idx != -1:
                    found_months.append((idx, mon))
            
            # Ordena pela posição no texto
            found_months.sort()
            
            if found_months:
                processed_segment = True
                # Itera pelos meses encontrados no segmento (para casos como SBPA: JAN... FEB... MAR...)
                for i, (idx, mon) in enumerate(found_months):
                    # O texto deste mês vai do índice dele até o próximo mês ou fim da string
                    start_slice = idx + len(mon)
                    end_slice = found_months[i+1][0] if i + 1 < len(found_months) else len(segmento_limpo)
                    
                    nums_str = segmento_limpo[start_slice:end_slice]
                    
                    # Pega todos os números soltos
                    dias_list = []
                    for token in nums_str.replace(",", " ").split():
                        if token.isdigit() and len(token) <= 2:
                            dias_list.append(int(token))
                    
                    # Gera os slots
                    try:
                        mes_obj = datetime.strptime(mon, "%b")
                        for d in dias_list:
                            dt_base = datetime(y, mes_obj.month, d)
                            # Ajuste simples de ano (se mês é JAN e dt_b é NOV, provavel ser ano seguinte)
                            if dt_base.month < dt_b.month and (dt_b.month - dt_base.month) > 6:
                                dt_base = dt_base.replace(year=y+1)
                            elif dt_base.month > dt_b.month and (dt_base.month - dt_b.month) > 6:
                                dt_base = dt_base.replace(year=y-1) # Raro
                            
                            if not dias_filtro or dt_base.weekday() in dias_filtro:
                                resultado.extend(extrair_horarios(horario_str, dt_base))
                    except: pass
            
            # 4. Caso Sobra: Números sem mês no início (herda do mês do item B ou anterior?)
            # Para SBRJ: JAN 27 28 -> Cai no 'found_months' acima.
            # Para caso bizarro onde começa só com número: "10 12 1000-1200"
            else:
                # Se só tem números
                tokens = segmento_limpo.split()
                if all(t.isdigit() for t in tokens) and len(tokens) > 0:
                     # Assume mês do item B
                    try:
                        for t in tokens:
                            dt_base = datetime(y, dt_b.month, int(t))
                            if not dias_filtro or dt_base.weekday() in dias_filtro:
                                resultado.extend(extrair_horarios(horario_str, dt_base))
                    except: pass

    return resultado

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """Função Mestre"""
    if not item_d_text or not item_d_text.strip(): return []

    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    if not dt_b or not dt_c: return []

    if (dt_c - dt_b).days > MAX_DAYS_PROJECT:
        dt_c = dt_b + timedelta(days=MAX_DAYS_PROJECT)

    text = item_d_text.upper().strip()
    text = text.replace('\n', ' ').replace(',', ' ').replace('.', ' ').replace('  ', ' ')
    
    # Limpezas
    text = RE_BARRA_DATA.sub(r'\1', text)
    text = RE_BARRA_DIA.sub(r'\1', text)
    # Remove caractere invisível comum em copy-paste
    text = text.replace(u'\xa0', u' ')

    # 1. TENTA SEGMENTAÇÃO (Resolve SBMQ, SBRJ, SBPA, SBGR)
    if RE_HORARIO_SEGMENT.search(text):
        res = processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao)
        if res: return res

    # 2. FALLBACKS
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

    # Ranges Semana
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

    # Dias Soltos
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