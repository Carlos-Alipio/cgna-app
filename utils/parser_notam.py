import re
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES ---
MAX_DAYS_PROJECT = 90
MONTHS_LIST = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# Regex pré-compiladas
RE_HORARIO_SEGMENT = re.compile(r'(\d{4}-\d{4}|SR-SS|SR-\d{4}|\d{4}-SS)')
RE_BARRA_DATA = re.compile(r'(\d{1,2})/\d{1,2}')
RE_BARRA_DIA = re.compile(r'(MON|TUE|WED|THU|FRI|SAT|SUN)/(MON|TUE|WED|THU|FRI|SAT|SUN)')

# Camada 1: Ranges Completos (DEC 31 TIL JAN 02)
RE_FULL_RANGE = re.compile(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+([A-Z]{3})\s+(\d{1,2})')

# Camada 2: Ranges Numéricos (19 TIL 20)
RE_NUM_RANGE = re.compile(r'(\d{1,2})\s+TIL\s+(\d{1,2})')

# Camada 3: Mês Isolado
RE_MONTH = re.compile(r'\b(' + '|'.join(MONTHS_LIST) + r')\b')

# Camada 4: Números Isolados
RE_NUM = re.compile(r'\b(\d{1,2})\b')

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
    Se a data lida for anterior ao mês de início da vigência,
    entende-se que é do ano seguinte.
    """
    if dt_alvo.month < dt_inicio_vigencia.month and dt_alvo.year == dt_inicio_vigencia.year:
        return dt_alvo.replace(year=dt_alvo.year + 1)
    return dt_alvo

def gerar_dias_entre(ini_dt, fim_dt, dias_filtro, horario_str):
    resultado = []
    if (fim_dt - ini_dt).days > MAX_DAYS_PROJECT:
        fim_dt = ini_dt + timedelta(days=MAX_DAYS_PROJECT)
    
    curr = ini_dt
    while curr <= fim_dt:
        if not dias_filtro or curr.weekday() in dias_filtro:
            resultado.extend(extrair_horarios(horario_str, curr))
        curr += timedelta(days=1)
    return resultado

def processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao):
    week_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}
    resultado = []
    
    # Encontra os delimitadores de horário
    matches = list(RE_HORARIO_SEGMENT.finditer(text))
    if not matches: return []

    last_end = 0
    y = dt_b.year
    
    # --- MEMÓRIA DE CONTEXTO ---
    # Começa com o mês do Item B. Essa variável persiste por todo o NOTAM.
    contexto_mes = dt_b.strftime("%b").upper()

    for match in matches:
        horario_str = match.group(1)
        segmento = text[last_end:match.start()].strip()
        last_end = match.end()
        
        if not segmento: continue

        # 1. Filtro Dias da Semana (Remove do texto para não confundir)
        dias_filtro = set()
        if any(d in segmento for d in week_map):
            for dia, idx in week_map.items():
                if dia in segmento:
                    dias_filtro.add(idx)
                    segmento = segmento.replace(dia, "") 
        
        segmento_limpo = segmento.strip()
        
        # --- LISTA DE EVENTOS ---
        # Vamos mapear tudo o que acontece neste segmento em ordem de posição
        eventos = [] # Tuplas: (posicao_inicio, tipo, dados)

        # A. Ranges Completos (DEC 31 TIL JAN 02)
        # Importante: Substituímos por espaços para manter os índices dos outros elementos
        for m in RE_FULL_RANGE.finditer(segmento_limpo):
            eventos.append((m.start(), 'FULL_RANGE', m.groups()))
            # Mascara o trecho encontrado com espaços para não ser pego pelas outras regex
            segmento_limpo = segmento_limpo[:m.start()] + " " * (m.end() - m.start()) + segmento_limpo[m.end():]

        # B. Ranges Parciais (10 TIL 20)
        for m in RE_NUM_RANGE.finditer(segmento_limpo):
            eventos.append((m.start(), 'PART_RANGE', m.groups()))
            segmento_limpo = segmento_limpo[:m.start()] + " " * (m.end() - m.start()) + segmento_limpo[m.end():]

        # C. Meses Isolados (JAN)
        for m in RE_MONTH.finditer(segmento_limpo):
            eventos.append((m.start(), 'MONTH', m.group(1)))
            segmento_limpo = segmento_limpo[:m.start()] + " " * (m.end() - m.start()) + segmento_limpo[m.end():]

        # D. Números Isolados (05)
        for m in RE_NUM.finditer(segmento_limpo):
            eventos.append((m.start(), 'NUM', m.group(1)))

        # Ordena eventos pela posição no texto
        eventos.sort(key=lambda x: x[0])

        # --- PROCESSAMENTO LINEAR ---
        for _, tipo, dados in eventos:
            if tipo == 'MONTH':
                # Atualiza a memória de contexto
                contexto_mes = dados
            
            elif tipo == 'FULL_RANGE':
                m1, d1, m2, d2 = dados
                try:
                    ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                    fim_dt = datetime.strptime(f"{y} {m2} {d2}", "%Y %b %d")
                    
                    ini_dt = ajustar_ano(ini_dt, dt_b)
                    # Lógica de virada de ano específica para range completo
                    if fim_dt.month < ini_dt.month: fim_dt = fim_dt.replace(year=ini_dt.year + 1)
                    else: fim_dt = fim_dt.replace(year=ini_dt.year)

                    resultado.extend(gerar_dias_entre(ini_dt, fim_dt, dias_filtro, horario_str))
                    # Atualiza contexto para o mês final do range
                    contexto_mes = m2
                except: pass

            elif tipo == 'PART_RANGE':
                d1, d2 = dados
                try:
                    mes_obj = datetime.strptime(contexto_mes, "%b")
                    ini_dt = datetime(y, mes_obj.month, int(d1))
                    fim_dt = datetime(y, mes_obj.month, int(d2))
                    
                    ini_dt = ajustar_ano(ini_dt, dt_b)
                    fim_dt = ajustar_ano(fim_dt, dt_b)
                    
                    resultado.extend(gerar_dias_entre(ini_dt, fim_dt, dias_filtro, horario_str))
                except: pass

            elif tipo == 'NUM':
                d1 = dados
                try:
                    mes_obj = datetime.strptime(contexto_mes, "%b")
                    dt_base = datetime(y, mes_obj.month, int(d1))
                    dt_base = ajustar_ano(dt_base, dt_b)
                    
                    if not dias_filtro or dt_base.weekday() in dias_filtro:
                        resultado.extend(extrair_horarios(horario_str, dt_base))
                except: pass

    # Filtro Final e Ordenação
    resultado_final = [r for r in resultado if dt_b <= r['inicio'] <= dt_c + timedelta(days=1)]
    unique_res = []
    seen = set()
    for r in resultado_final:
        key = (r['inicio'], r['fim'])
        if key not in seen:
            seen.add(key)
            unique_res.append(r)
            
    return sorted(unique_res, key=lambda x: x['inicio'])

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

    # FALLBACKS
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
        return gerar_dias_entre(dt_b, dt_c, dias_exc, horarios_str)

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