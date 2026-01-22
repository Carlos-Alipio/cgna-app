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
RE_DIA_COMPOSTO = re.compile(r'\b([A-Z]{3})/([A-Z]{3})\b')

# Regex flexível para datas com barra (DEC 01/02)
RE_DATA_BARRA = re.compile(r'([A-Z]{3})\s+(\d{1,2})\s*/\s*(\d{1,2})(?:\s|$)')

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

def verifica_virada_noite(horario_str):
    """
    Verifica se o string de horário implica virada de dia (ex: 2133-0115).
    Retorna True se Hora Fim < Hora Início.
    """
    try:
        parts = horario_str.replace(" TO ", "-").split("-")
        if len(parts) < 2: return False
        h1, h2 = parts[0].strip(), parts[1].strip()
        
        # Casos SR/SS
        if "SS" in h1 and "SR" in h2: return True # Pôr do sol ao nascer (vira noite)
        if "SR" in h1 and "SS" in h2: return False # Dia claro
        
        # Numéricos
        if h1.isdigit() and h2.isdigit() and len(h1)==4 and len(h2)==4:
            return int(h2) < int(h1)
            
        return False
    except:
        return False

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
    contexto_validade = None 

    for match in matches:
        horario_str = match.group(1)
        segmento = text[last_end:match.start()].strip()
        last_end = match.end()
        
        # --- ETAPA 0: PROCURA DATA COM BARRA (DEC 01/02) ---
        ini_dt_seg = None
        fim_dt_seg = None
        achou_data = False
        eh_evento_unico = False # Flag para travar o loop no primeiro dia

        m_barra = RE_DATA_BARRA.search(segmento)
        if m_barra:
            m1, d1, d2 = m_barra.groups()
            try:
                mes_num = MONTH_MAP.get(m1)
                if mes_num:
                    ini_dt_seg = datetime(y, mes_num, int(d1))
                    fim_dt_seg = datetime(y, mes_num, int(d2))
                    ini_dt_seg = ajustar_ano(ini_dt_seg, dt_b)
                    
                    if fim_dt_seg.month < ini_dt_seg.month:
                        fim_dt_seg = fim_dt_seg.replace(year=ini_dt_seg.year + 1)
                    else:
                        fim_dt_seg = fim_dt_seg.replace(year=ini_dt_seg.year)
                    
                    achou_data = True
                    contexto_validade = (ini_dt_seg, fim_dt_seg)

                    # === CORREÇÃO LÓGICA DO USUÁRIO ===
                    # Se for dias consecutivos (ex: 01 e 02) E o horário vira a noite (2133-0115)
                    # Significa "Do dia 01 às 21h ATÉ o dia 02 às 01h".
                    # NÃO significa repetir no dia 02.
                    diff_dias = (fim_dt_seg - ini_dt_seg).days
                    vira_noite = verifica_virada_noite(horario_str)
                    
                    if diff_dias == 1 and vira_noite:
                        # Forçamos o fim para ser igual ao início para o gerador rodar só 1 vez
                        # O cálculo de horário (+1 dia) fará chegar na data final correta
                        fim_dt_seg = ini_dt_seg 
            except: pass

        # --- ETAPA 1: LIMPEZA ---
        segmento_limpo = RE_DIA_COMPOSTO.sub(r'\1', segmento)
        segmento_limpo = segmento_limpo.replace("/", " ") 

        # --- ETAPA 2: DIAS DA SEMANA ---
        dias_filtro = set()
        for m_wr in RE_WEEK_RANGE.finditer(segmento_limpo):
            d1_str, d2_str = m_wr.groups()
            s_idx = WEEK_MAP[d1_str]
            e_idx = WEEK_MAP[d2_str]
            if s_idx <= e_idx: dias_filtro.update(range(s_idx, e_idx + 1))
            else: dias_filtro.update(list(range(s_idx, 7)) + list(range(0, e_idx + 1)))
        
        segmento_sem_week = RE_WEEK_RANGE.sub(" ", segmento_limpo)
        for dia_nome, dia_idx in WEEK_MAP.items():
            if re.search(r'\b' + dia_nome + r'\b', segmento_sem_week):
                dias_filtro.add(dia_idx)
        
        # --- ETAPA 3: OUTRAS DATAS ---
        if not achou_data:
            segmento_datas = segmento_sem_week
            for dia in WEEK_MAP.keys(): 
                segmento_datas = re.sub(r'\b' + dia + r'\b', " ", segmento_datas)
            
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
                        contexto_validade = (ini_dt_seg, fim_dt_seg)
                except: pass
        
        # --- ETAPA 4: GERAÇÃO ---
        if not achou_data and contexto_validade:
            ini_dt_seg, fim_dt_seg = contexto_validade
        
        if ini_dt_seg and fim_dt_seg:
            resultado.extend(gerar_dias_entre(ini_dt_seg, fim_dt_seg, dias_filtro, horario_str))
        else:
            if dias_filtro:
                resultado.extend(gerar_dias_entre(dt_b, dt_c, dias_filtro, horario_str))

    # Sem tolerância (lógica exata)
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

    text = item_d_text.upper().strip()
    text = text.replace('\n', ' ').replace(',', ' ').replace('.', ' ').replace('  ', ' ')
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