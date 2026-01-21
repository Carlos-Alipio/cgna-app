import re
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES ---
MAX_DAYS_PROJECT = 365 

# Dicionários de Tradução
MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    "FEV": 2, "ABR": 4, "MAI": 5, "AGO": 8, "SET": 9, "OUT": 10, "DEZ": 12
}

WEEK_MAP = {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6,
    "SEG": 0, "TER": 1, "QUA": 2, "QUI": 3, "SEX": 4, "SAB": 5, "DOM": 6
}

days_pattern = '|'.join(WEEK_MAP.keys())

# --- REGEX ---
RE_HORARIO_SEGMENT = re.compile(r'(\d{4}-\d{4}|SR-SS|SR-\d{4}|\d{4}-SS)')
RE_BARRA_DATA = re.compile(r'(\d{1,2})/\d{1,2}')
RE_BARRA_DIA = re.compile(r'(' + days_pattern + r')/(' + days_pattern + r')')
RE_WEEK_RANGE = re.compile(r'\b(' + days_pattern + r')\s+TIL\s+(' + days_pattern + r')\b')
RE_FULL_RANGE = re.compile(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+([A-Z]{3})\s+(\d{1,2})')
RE_NUM_RANGE = re.compile(r'(\d{1,2})\s+TIL\s+(\d{1,2})')
RE_MONTH = re.compile(r'\b(' + '|'.join(MONTH_MAP.keys()) + r')\b')
RE_NUM = re.compile(r'\b(\d{1,2})\b')

def parse_notam_date(date_str):
    try:
        if not date_str: return None
        # Se contiver PERM, retorna None (será tratado na função mestre)
        if "PERM" in str(date_str).upper(): return None
        
        clean_str = str(date_str).replace("-", "").replace(":", "").replace(" ", "").strip()
        if len(clean_str) != 10: return None
        return datetime.strptime(clean_str, "%y%m%d%H%M")
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
    resultado = []
    matches = list(RE_HORARIO_SEGMENT.finditer(text))
    if not matches: return []

    last_end = 0
    y = dt_b.year
    contexto_mes = dt_b.strftime("%b").upper()
    ultimo_segmento_valido = None

    for match in matches:
        horario_str = match.group(1)
        segmento = text[last_end:match.start()].strip()
        last_end = match.end()
        
        tem_conteudo = (re.search(r'\d', segmento) or re.search(r'[A-Z]{3}', segmento))
        if not tem_conteudo and ultimo_segmento_valido:
            segmento = ultimo_segmento_valido
        elif tem_conteudo:
            ultimo_segmento_valido = segmento
        elif not tem_conteudo and not ultimo_segmento_valido:
            continue
            
        dias_filtro = set()
        for m_wr in RE_WEEK_RANGE.finditer(segmento):
            d1_str, d2_str = m_wr.groups()
            s_idx = WEEK_MAP[d1_str]
            e_idx = WEEK_MAP[d2_str]
            if s_idx <= e_idx: dias_filtro.update(range(s_idx, e_idx + 1))
            else: dias_filtro.update(list(range(s_idx, 7)) + list(range(0, e_idx + 1)))
        segmento = RE_WEEK_RANGE.sub(" ", segmento)

        for dia_nome, dia_idx in WEEK_MAP.items():
            if re.search(r'\b' + dia_nome + r'\b', segmento):
                dias_filtro.add(dia_idx)
                segmento = re.sub(r'\b' + dia_nome + r'\b', " ", segmento)
        
        segmento_limpo = segmento.strip()
        
        eventos = []
        for m in RE_FULL_RANGE.finditer(segmento_limpo):
            eventos.append((m.start(), 'FULL_RANGE', m.groups()))
            segmento_limpo = segmento_limpo[:m.start()] + " " * (m.end() - m.start()) + segmento_limpo[m.end():]
        for m in RE_NUM_RANGE.finditer(segmento_limpo):
            eventos.append((m.start(), 'PART_RANGE', m.groups()))
            segmento_limpo = segmento_limpo[:m.start()] + " " * (m.end() - m.start()) + segmento_limpo[m.end():]
        for m in RE_MONTH.finditer(segmento_limpo):
            eventos.append((m.start(), 'MONTH', m.group(1)))
            segmento_limpo = segmento_limpo[:m.start()] + " " * (m.end() - m.start()) + segmento_limpo[m.end():]
        for m in RE_NUM.finditer(segmento_limpo):
            eventos.append((m.start(), 'NUM', m.group(1)))

        eventos.sort(key=lambda x: x[0])

        for _, tipo, dados in eventos:
            if tipo == 'MONTH':
                contexto_mes = dados
            elif tipo == 'FULL_RANGE':
                m1, d1, m2, d2 = dados
                try:
                    mes1_num = MONTH_MAP.get(m1)
                    mes2_num = MONTH_MAP.get(m2)
                    if mes1_num and mes2_num:
                        ini_dt = datetime(y, mes1_num, int(d1))
                        fim_dt = datetime(y, mes2_num, int(d2))
                        ini_dt = ajustar_ano(ini_dt, dt_b)
                        if fim_dt.month < ini_dt.month: fim_dt = fim_dt.replace(year=ini_dt.year + 1)
                        else: fim_dt = fim_dt.replace(year=ini_dt.year)
                        resultado.extend(gerar_dias_entre(ini_dt, fim_dt, dias_filtro, horario_str))
                        contexto_mes = m2
                except: pass
            elif tipo == 'PART_RANGE':
                d1, d2 = dados
                try:
                    mes_num = MONTH_MAP.get(contexto_mes)
                    if mes_num:
                        ini_dt = datetime(y, mes_num, int(d1))
                        fim_dt = datetime(y, mes_num, int(d2))
                        ini_dt = ajustar_ano(ini_dt, dt_b)
                        fim_dt = ajustar_ano(fim_dt, dt_b)
                        resultado.extend(gerar_dias_entre(ini_dt, fim_dt, dias_filtro, horario_str))
                except: pass
            elif tipo == 'NUM':
                d1 = dados
                try:
                    mes_num = MONTH_MAP.get(contexto_mes)
                    if mes_num:
                        dt_base = datetime(y, mes_num, int(d1))
                        dt_base = ajustar_ano(dt_base, dt_b)
                        if not dias_filtro or dt_base.weekday() in dias_filtro:
                            resultado.extend(extrair_horarios(horario_str, dt_base))
                except: pass

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
    # 1. PROCESSA DATA B
    dt_b = parse_notam_date(item_b_raw)
    if not dt_b: return []

    # 2. PROCESSA DATA C
    # Verifica PERM explícito na string crua
    is_perm_raw = item_c_raw and "PERM" in str(item_c_raw).upper()
    dt_c = parse_notam_date(item_c_raw)
    
    # REGRA DE PROJEÇÃO: Se PERM ou Vazio -> B + 365 dias
    if is_perm_raw or not dt_c:
        dt_c = dt_b + timedelta(days=365)

    # 3. ATIVIDADE CONTÍNUA (D Vazio)
    if not item_d_text or not str(item_d_text).strip():
        return [{'inicio': dt_b, 'fim': dt_c}]

    # 4. TRAVA DE SEGURANÇA
    if (dt_c - dt_b).days > MAX_DAYS_PROJECT:
        dt_c = dt_b + timedelta(days=MAX_DAYS_PROJECT)

    # 5. PARSER NORMAL
    text = item_d_text.upper().strip()
    text = text.replace('\n', ' ').replace(',', ' ').replace('.', ' ').replace('  ', ' ')
    text = RE_BARRA_DATA.sub(r'\1', text)
    text = RE_BARRA_DIA.sub(r'\1', text)
    text = text.replace(u'\xa0', u' ')

    res = []
    
    # Tentativa 1: Segmentação por Horário
    if RE_HORARIO_SEGMENT.search(text):
        res = processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao)
    
    # Tentativa 2: DLY/DAILY
    if not res:
        if "DLY" in text or "DAILY" in text:
            horarios_str = text.replace("DLY", "").replace("DAILY", "").strip()
            dias_exc = set()
            if "EXC" in horarios_str:
                parts = horarios_str.split("EXC")
                horarios_str = parts[0].strip()
                exc_text = parts[1].strip()
                for k, v in WEEK_MAP.items():
                    if k in exc_text: dias_exc.add(v)
            res = gerar_dias_entre(dt_b, dt_c, dias_exc, horarios_str)
    
    # Tentativa 3: TIL (Ranges de Dia da Semana)
    if not res:
        m_week = re.search(r'\b(' + days_pattern + r')\s+TIL\s+(' + days_pattern + r')\b', text)
        if m_week:
            s_idx = WEEK_MAP[m_week.group(1)]
            e_idx = WEEK_MAP[m_week.group(2)]
            validos = set(range(s_idx, e_idx + 1)) if s_idx <= e_idx else set(list(range(s_idx, 7)) + list(range(0, e_idx + 1)))
            horario = text.replace(m_week.group(0), "").strip()
            temp_res = []
            curr = dt_b
            while curr <= dt_c:
                if curr.weekday() in validos:
                    temp_res.extend(extrair_horarios(horario, curr))
                curr += timedelta(days=1)
            res = temp_res

    # Tentativa 4: Dias Específicos (MON, TUE...)
    if not res:
        if any(d in text for d in WEEK_MAP):
            alvo = {WEEK_MAP[d] for d in WEEK_MAP if d in text}
            horario = text
            for d in WEEK_MAP: horario = horario.replace(d, "")
            temp_res = []
            curr = dt_b
            while curr <= dt_c:
                if curr.weekday() in alvo:
                    temp_res.extend(extrair_horarios(horario, curr))
                curr += timedelta(days=1)
            res = temp_res
            
    # 6. FALLBACK FINAL (H24 PARA TEXTO DESCRITIVO SEM HORÁRIOS)
    if not res:
         return [{'inicio': dt_b, 'fim': dt_c}]

    return res