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

# Camada 2: Ranges Numéricos (19 TIL 20) - Usado dentro do contexto de um mês
RE_NUM_RANGE = re.compile(r'(\d{1,2})\s+TIL\s+(\d{1,2})')

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
    Se a data encontrada for anterior ao início da vigência (considerando o mês),
    entende-se que é do ano seguinte.
    """
    # Ex: Vigência começa em DEZ/2025. Data lida é JAN. JAN < DEZ, logo é 2026.
    if dt_alvo.month < dt_inicio_vigencia.month and dt_alvo.year == dt_inicio_vigencia.year:
        return dt_alvo.replace(year=dt_alvo.year + 1)
    return dt_alvo

def gerar_dias_entre(ini_dt, fim_dt, dias_filtro, horario_str):
    """Gera slots de horário entre duas datas, respeitando filtro de dias."""
    resultado = []
    # Trava de segurança para loops infinitos ou datas erradas
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
    
    # 1. Encontra os horários (delimitadores)
    matches = list(RE_HORARIO_SEGMENT.finditer(text))
    if not matches: return []

    last_end = 0
    y = dt_b.year

    for match in matches:
        horario_str = match.group(1)
        # Pega todo o texto de datas antes deste horário
        segmento = text[last_end:match.start()].strip()
        last_end = match.end()
        
        if not segmento: continue

        # 2. Extrai Filtros de Dia da Semana (MON, TUE...) e remove do texto
        dias_filtro = set()
        if any(d in segmento for d in week_map):
            for dia, idx in week_map.items():
                if dia in segmento:
                    dias_filtro.add(idx)
                    segmento = segmento.replace(dia, "") 
        
        segmento_limpo = segmento.strip()

        # --- FASE A: Extrair Ranges Completos (Cross-Month) ---
        # Ex: "DEC 31 TIL JAN 02"
        # Encontramos, processamos e REMOVEMOS do texto para não duplicar.
        for m in RE_FULL_RANGE.finditer(segmento_limpo):
            m1, d1, m2, d2 = m.groups()
            try:
                ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                fim_dt = datetime.strptime(f"{y} {m2} {d2}", "%Y %b %d")
                
                ini_dt = ajustar_ano(ini_dt, dt_b)
                # Lógica de virada de ano para o fim do range
                if fim_dt.month < ini_dt.month: fim_dt = fim_dt.replace(year=ini_dt.year + 1)
                else: fim_dt = fim_dt.replace(year=ini_dt.year)

                resultado.extend(gerar_dias_entre(ini_dt, fim_dt, dias_filtro, horario_str))
            except: pass
        
        # Remove os ranges completos já processados
        segmento_limpo = RE_FULL_RANGE.sub(" ", segmento_limpo)

        # --- FASE B: Processar por Mês (Ranges Parciais e Listas) ---
        # Agora sobrou algo como "DEC 19 TIL 20 29 TIL 31 JAN 01 TIL 03"
        
        # Mapeia onde está cada mês no texto
        found_months = []
        for mon in MONTHS_LIST:
            for m in re.finditer(mon, segmento_limpo):
                found_months.append((m.start(), mon))
        found_months.sort()

        # Se não achou mês, tenta usar o mês do Item B (para casos como "10 12 15...")
        if not found_months:
            # Cria um "mês falso" no início para entrar no loop
            found_months = [(0, dt_b.strftime("%b").upper())]

        # Itera sobre cada bloco de mês encontrado
        for i, (idx, mon) in enumerate(found_months):
            # Define o texto que pertence a este mês (vai até o próximo mês ou fim da string)
            start_slice = idx + len(mon) if idx > 0 else 0 # Pula o nome do mês, exceto se for o fallback
            if i + 1 < len(found_months):
                end_slice = found_months[i+1][0]
            else:
                end_slice = len(segmento_limpo)
            
            chunk = segmento_limpo[start_slice:end_slice]
            
            # 1. Ranges Parciais dentro do Chunk ("19 TIL 20")
            for m in RE_NUM_RANGE.finditer(chunk):
                d1, d2 = m.groups()
                try:
                    mes_obj = datetime.strptime(mon, "%b")
                    ini_dt = datetime(y, mes_obj.month, int(d1))
                    fim_dt = datetime(y, mes_obj.month, int(d2))
                    
                    ini_dt = ajustar_ano(ini_dt, dt_b)
                    fim_dt = ajustar_ano(fim_dt, dt_b) # Assume mesmo ano/virada

                    resultado.extend(gerar_dias_entre(ini_dt, fim_dt, dias_filtro, horario_str))
                except: pass
            
            # Remove os ranges parciais para sobrar só números soltos
            chunk_sem_ranges = RE_NUM_RANGE.sub(" ", chunk)

            # 2. Números Soltos ("05 08 12")
            numeros = re.findall(r'\d+', chunk_sem_ranges)
            for num in numeros:
                # Ignora se for muito longo (provavelmente lixo)
                if len(num) > 2: continue
                try:
                    mes_obj = datetime.strptime(mon, "%b")
                    dt_base = datetime(y, mes_obj.month, int(num))
                    dt_base = ajustar_ano(dt_base, dt_b)
                    
                    if not dias_filtro or dt_base.weekday() in dias_filtro:
                        resultado.extend(extrair_horarios(horario_str, dt_base))
                except: pass

    # Filtro Final: Remove datas fora da vigência global do NOTAM
    resultado_final = [r for r in resultado if dt_b <= r['inicio'] <= dt_c + timedelta(days=1)]
    
    # Ordena e remove duplicatas (caso haja sobreposição)
    # Convertendo para tupla para usar set, depois volta para dict
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

    # 1. Estratégia Principal: Segmentação por Horário
    if RE_HORARIO_SEGMENT.search(text):
        res = processar_por_segmentacao_de_horario(text, dt_b, dt_c, icao)
        if res: return res

    # 2. Fallbacks (Mantidos para compatibilidade com textos simples como "DLY")
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
        return gerar_dias_entre(dt_b, dt_c, dias_exc, horarios_str) # Invertido logica exc

    return []