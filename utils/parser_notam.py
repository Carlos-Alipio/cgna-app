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
# Captura horários robustos (1000-1200, 1000 - 1200, SR-SS)
RE_HORARIO_SEGMENT = re.compile(r'\b(SR|SS|\d{4})\s?-\s?(SR|SS|\d{4})\b')

RE_DIA_COMPOSTO = re.compile(r'\b([A-Z]{3})/([A-Z]{3})\b')
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
    try:
        parts = horario_str.replace(" TO ", "-").split("-")
        if len(parts) < 2: return False
        h1, h2 = parts[0].strip(), parts[1].strip()
        if "SS" in h1 and "SR" in h2: return True
        if "SR" in h1 and "SS" in h2: return False
        if h1.isdigit() and h2.isdigit() and len(h1)==4 and len(h2)==4:
            return int(h2) < int(h1)
        return False
    except:
        return False

def extrair_horarios(texto_horario, base_date):
    slots = []
    # Usa Regex para capturar pares de horário, ignorando espaços internos
    matches = RE_HORARIO_SEGMENT.findall(texto_horario.upper())
    
    sr_dt, ss_dt = calculate_sun_times(base_date)

    for inicio_str, fim_str in matches:
        try:
            dt_ini, dt_fim = None, None

            if "SR" in inicio_str: dt_ini = sr_dt
            elif "SS" in inicio_str: dt_ini = ss_dt
            elif len(inicio_str) == 4 and inicio_str.isdigit():
                dt_ini = base_date.replace(hour=int(inicio_str[:2]), minute=int(inicio_str[2:]))

            if "SR" in fim_str: dt_fim = sr_dt
            elif "SS" in fim_str: dt_fim = ss_dt
            elif len(fim_str) == 4 and fim_str.isdigit():
                dt_fim = base_date.replace(hour=int(fim_str[:2]), minute=int(fim_str[2:]))
                if dt_fim < dt_ini: dt_fim += timedelta(days=1)

            if dt_ini and dt_fim:
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
    
    # --- MEMÓRIA DE CONTEXTO EXPANDIDA ---
    last_contexto = {
        'validade': None,        # (ini, fim) para ranges
        'dias_filtro': set(),    # {0, 2, 4} para dias da semana
        'datas_pontuais': [],    # [datetime1, datetime2] para dias soltos (NOVO!)
        'is_dly': False          # Flag DLY
    }

    for match in matches:
        horario_str = match.group(0)
        segmento = text[last_end:match.start()].strip()
        last_end = match.end()
        
        # Variáveis locais para este segmento
        ini_dt_seg = None
        fim_dt_seg = None
        achou_data = False
        dias_filtro = set()
        datas_pontuais = [] # Nova variável local
        is_dly = False

        tem_conteudo = bool(re.search(r'[A-Z0-9]', segmento))

        if not tem_conteudo:
            # === HERANÇA DE CONTEXTO ===
            ini_dt_seg, fim_dt_seg = last_contexto['validade'] if last_contexto['validade'] else (None, None)
            dias_filtro = last_contexto['dias_filtro'].copy()
            datas_pontuais = last_contexto['datas_pontuais'].copy() # Herda a lista de datas
            is_dly = last_contexto['is_dly']
            
            if ini_dt_seg or datas_pontuais: achou_data = True
            
        else:
            # === PARSE DE NOVO CONTEXTO ===
            
            if "DLY" in segmento or "DAILY" in segmento: is_dly = True

            # ETAPA 0: DATA COM BARRA
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
                        contexto_mes = m1 

                        diff_dias = (fim_dt_seg - ini_dt_seg).days
                        vira_noite = verifica_virada_noite(horario_str)
                        if diff_dias == 1 and vira_noite:
                            fim_dt_seg = ini_dt_seg 
                except: pass

            # ETAPA 1: LIMPEZA
            segmento_limpo = RE_DIA_COMPOSTO.sub(r'\1', segmento)
            segmento_limpo = segmento_limpo.replace("/", " ") 

            # ETAPA 2: DIAS DA SEMANA
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
            
            # ETAPA 3: RANGES COMPLETOS
            segmento_datas = segmento_sem_week
            for dia in WEEK_MAP.keys(): 
                segmento_datas = re.sub(r'\b' + dia + r'\b', " ", segmento_datas)

            if not achou_data:
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
                            contexto_mes = m2
                    except: pass

            # ETAPA 4: DIAS SOLTOS
            if not achou_data:
                m_mes = RE_MONTH.search(segmento_datas)
                if m_mes: contexto_mes = m_mes.group(1)
                
                numeros_encontrados = list(RE_NUM.finditer(segmento_datas))
                if numeros_encontrados:
                    mes_num = MONTH_MAP.get(contexto_mes)
                    if mes_num:
                        for m_num in numeros_encontrados:
                            dia_num = int(m_num.group(1))
                            if 1 <= dia_num <= 31: 
                                try:
                                    dt_pontual = datetime(y, mes_num, dia_num)
                                    dt_pontual = ajustar_ano(dt_pontual, dt_b)
                                    datas_pontuais.append(dt_pontual)
                                except: pass
                        if datas_pontuais:
                            achou_data = True
            
            # ATUALIZA A MEMÓRIA PARA O PRÓXIMO LOOP
            # Se achou dados novos, substitui a memória. Se não, mantém a anterior (se vazio) ou reseta.
            
            if achou_data:
                # Prioridade: Datas Pontuais zeram Validade e vice-versa, pois são modos excludentes
                if datas_pontuais:
                    last_contexto['datas_pontuais'] = datas_pontuais
                    last_contexto['validade'] = None # Anula range anterior
                elif ini_dt_seg and fim_dt_seg:
                    last_contexto['validade'] = (ini_dt_seg, fim_dt_seg)
                    last_contexto['datas_pontuais'] = [] # Anula lista anterior
            
            if dias_filtro: last_contexto['dias_filtro'] = dias_filtro
            if is_dly: last_contexto['is_dly'] = True

        # --- GERAÇÃO FINAL DO SEGMENTO ---
        
        # Modo 1: Datas Pontuais (Prioridade máxima se existir)
        if datas_pontuais:
             for dt in datas_pontuais:
                resultado.extend(extrair_horarios(horario_str, dt))
        
        # Modo 2: Range Contínuo (ou memória de range)
        elif ini_dt_seg and fim_dt_seg:
            resultado.extend(gerar_dias_entre(ini_dt_seg, fim_dt_seg, dias_filtro, horario_str))
        
        # Modo 3: Fallback (Período Total do NOTAM)
        elif is_dly or dias_filtro:
            resultado.extend(gerar_dias_entre(dt_b, dt_c, dias_filtro, horario_str))

    # Filtragem Final
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
    text = text.replace('\n', ' ').replace('\t', ' ').replace(',', ' ').replace('.', ' ').replace('  ', ' ')
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