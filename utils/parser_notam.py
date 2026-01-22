import re
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES ---
MAX_DAYS_PROJECT = 365 

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

# Regex para limpar dias compostos ex: MON/TUE -> MON
RE_DIA_COMPOSTO = re.compile(r'\b([A-Z]{3})/([A-Z]{3})\b')

RE_WEEK_RANGE = re.compile(r'\b(' + days_pattern + r')\s+TIL\s+(' + days_pattern + r')\b')
RE_FULL_RANGE = re.compile(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+([A-Z]{3})\s+(\d{1,2})')
RE_NUM_RANGE = re.compile(r'(\d{1,2})\s+TIL\s+(\d{1,2})')
RE_MONTH = re.compile(r'\b(' + '|'.join(MONTH_MAP.keys()) + r')\b')
RE_NUM = re.compile(r'\b(\d{1,2})\b')

def parse_notam_date(date_str):
    try:
        if not date_str: return None
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
    
    # MEMÓRIA: Guarda a última data válida encontrada
    contexto_validade = None 

    for match in matches:
        horario_str = match.group(1)
        segmento = text[last_end:match.start()].strip()
        last_end = match.end()
        
        # 1. Limpeza de Dias Compostos (CRUCIAL para FRI/SAT)
        # Transforma "MON/TUE" em "MON". O horário (ex: 1940-0115) cuidará da virada do dia.
        segmento_limpo = RE_DIA_COMPOSTO.sub(r'\1', segmento)
        segmento_limpo = segmento_limpo.replace("/", " ") # Remove barras restantes

        # 2. Identificação de Dias da Semana
        dias_filtro = set()
        
        # Ranges (MON TIL FRI)
        for m_wr in RE_WEEK_RANGE.finditer(segmento_limpo):
            d1_str, d2_str = m_wr.groups()
            s_idx = WEEK_MAP[d1_str]
            e_idx = WEEK_MAP[d2_str]
            if s_idx <= e_idx: dias_filtro.update(range(s_idx, e_idx + 1))
            else: dias_filtro.update(list(range(s_idx, 7)) + list(range(0, e_idx + 1)))
        
        segmento_sem_week = RE_WEEK_RANGE.sub(" ", segmento_limpo)

        # Dias Individuais (MON TUE WED)
        for dia_nome, dia_idx in WEEK_MAP.items():
            if re.search(r'\b' + dia_nome + r'\b', segmento_sem_week):
                dias_filtro.add(dia_idx)
        
        # 3. Identificação de Datas
        segmento_datas = segmento_sem_week
        for dia in WEEK_MAP.keys(): # Remove nomes de dias para achar datas
            segmento_datas = re.sub(r'\b' + dia + r'\b', " ", segmento_datas)
        
        ini_dt_seg = None
        fim_dt_seg = None
        achou_data = False

        # Procura Range Completo (DEC 02 TIL FEB 28)
        m_full = RE_FULL_RANGE.search(segmento_datas)
        if m_full:
            m1, d1, m2, d2 = m_full.groups()
            try:
                mes1_num = MONTH_MAP.get(m1)
                mes2_num = MONTH_MAP.get(m2)
                if mes1_num and mes2_num:
                    ini_dt_seg = datetime(y, mes1_num, int(d1))
                    fim_dt_seg = datetime(y, mes2_num, int(d2))
                    ini_dt_seg = ajustar_ano(ini_dt_seg, dt_b)
                    
                    if fim_dt_seg.month < ini_dt_seg.month: 
                        fim_dt_seg = fim_dt_seg.replace(year=ini_dt_seg.year + 1)
                    else: 
                        fim_dt_seg = fim_dt_seg.replace(year=ini_dt_seg.year)
                    
                    achou_data = True
                    contexto_validade = (ini_dt_seg, fim_dt_seg) # Atualiza memória
            except: pass
        
        # 4. Aplicação da Lógica de Memória
        if not achou_data and contexto_validade:
            # Se não achou data nova, mas tem memória, usa a memória
            ini_dt_seg, fim_dt_seg = contexto_validade
        
        # 5. Geração
        if ini_dt_seg and fim_dt_seg:
            resultado.extend(gerar_dias_entre(ini_dt_seg, fim_dt_seg, dias_filtro, horario_str))
        else:
            # Se não tem memória nem data, usa B e C
            if dias_filtro:
                resultado.extend(gerar_dias_entre(dt_b, dt_c, dias_filtro, horario_str))

    # Limpeza e Ordenação
    resultado_final = [r for r in resultado if dt_b <= r['inicio'] <= dt_c + timedelta(days=2)]
    unique_res = []
    seen = set()
    for r in resultado_final:
        key = (r['inicio'], r['fim'])
        if key not in seen:
            seen.add(key)
            unique_res.append(r)
            
    return sorted(unique_res, key=lambda x: x['inicio'])

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    # Processamento de Datas Iniciais
    dt_b = parse_notam_date(item_b_raw)
    if not dt_b: return []

    val_c = str(item_c_raw).upper()
    dt_c = parse_notam_date(item_c_raw)
    
    if "PERM" in val_c or not dt_c:
        dt_c = dt_b + timedelta(days=365)

    if not item_d_text or not str(item_d_text).strip():
        return [{'inicio': dt_b, 'fim': dt_c}]

    if (dt_c - dt_b).days > MAX_DAYS_PROJECT:
        dt_c = dt_b + timedelta(days=MAX_DAYS_PROJECT)

    # Limpeza do Texto
    text = item_d_text.upper().strip()
    text = text.replace('\n', ' ').replace(',', ' ').replace('.', ' ').replace('  ', ' ')
    text = RE_BARRA_DATA.sub(r'\1', text) 
    text = text.replace(u'\xa0', u' ')

    res = []
    if RE_HORARIO_SEGMENT.search(text):
        res = processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao)
    
    if not res:
        if "DLY" in text or "DAILY" in text:
            horarios_str = text.replace("DLY", "").replace("DAILY", "").strip()
            res = gerar_dias_entre(dt_b, dt_c, set(), horarios_str)

    if not res:
         return [{'inicio': dt_b, 'fim': dt_c}]

    return res