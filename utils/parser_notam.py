import re
from datetime import datetime, timedelta

def parse_notam_date(date_str):
    """Converte string YYMMDDHHMM em datetime object"""
    try:
        if not date_str or len(str(date_str)) != 10: return None
        return datetime.strptime(str(date_str), "%y%m%d%H%M")
    except: return None

def calculate_sun_times(date_obj, lat, lon):
    """Horários solares fictícios para teste (09z-21z)"""
    sr = date_obj.replace(hour=9, minute=0, second=0)
    ss = date_obj.replace(hour=21, minute=0, second=0)
    return sr, ss

def extrair_horarios(texto_horario, base_date, icao):
    """Lê strings de hora: '1000-1500', 'SR-SS'"""
    slots = []
    texto_clean = texto_horario.upper().replace("/", "-").replace(" TO ", "-").strip()
    partes = re.split(r'\s+AND\s+|\s+', texto_clean)
    sr_dt, ss_dt = calculate_sun_times(base_date, 0, 0)

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

def limpar_barras_datas(text):
    """Limpa 07/08 -> 07 e MON/TUE -> MON"""
    text = re.sub(r'(\d{1,2})/\d{1,2}', r'\1', text)
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    pattern_days = r'(' + '|'.join(days) + r')/(' + '|'.join(days) + r')'
    text = re.sub(pattern_days, r'\1', text)
    return text

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    Função Mestre: Processa Item D com suporte a Blocos Complexos.
    """
    if not item_d_text or not item_d_text.strip(): return []

    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    if not dt_b or not dt_c: return []

    resultado_final = []
    
    # 1. Limpeza
    text = item_d_text.upper().strip()
    text = text.replace('\n', ' ').replace(',', ' ').replace('.', ' ').replace('  ', ' ')
    text = limpar_barras_datas(text)

    # Mapa de Dias
    week_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}

    # ==========================================================================
    # CASO: BLOCOS COMPLEXOS (SBGR)
    # Padrão: MES...HORA MES...HORA (Múltiplos na mesma linha)
    # Regex busca: (MES + qualquer coisa + HORA-HORA)
    # ==========================================================================
    # Explicação Regex: 
    # [A-Z]{3} (Mês) + .+? (Texto não guloso) + \d{4}-\d{4} (Horário)
    pattern_blocks = r'([A-Z]{3}\s+.+?\d{4}-\d{4})'
    
    # Verifica se tem esse padrão de horário no final
    if re.search(r'\d{4}-\d{4}', text) and re.match(r'^[A-Z]{3}', text):
        blocks = re.findall(pattern_blocks, text)
        
        # Se achou blocos, processa cada um individualmente
        if blocks:
            for block in blocks:
                # 1. Extrai Horário (Está sempre no fim do bloco capturado)
                match_time = re.search(r'(\d{4}-\d{4})', block)
                if not match_time: continue
                hora_txt = match_time.group(1)
                
                # 2. Identifica Dias da Semana (Filtros)
                dias_filtro = []
                for dia, idx in week_map.items():
                    if dia in block:
                        dias_filtro.append(idx)
                
                # 3. Limpa o bloco para sobrar só a Data (Remove hora e dias semana)
                data_part = block.replace(hora_txt, "")
                for dia in week_map.keys():
                    data_part = data_part.replace(dia, "")
                data_part = data_part.strip()

                # 4. Interpreta o Range de Datas (JAN 10 TIL 16 ou JAN 11 TIL JAN 26)
                ini_dt = None
                fim_dt = None
                
                # Sub-caso A: "JAN 11 TIL JAN 26" (Mês explícito nos dois)
                match_full = re.search(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+([A-Z]{3})\s+(\d{1,2})', data_part)
                
                # Sub-caso B: "JAN 10 TIL 16" (Mês implícito no fim)
                match_partial = re.search(r'([A-Z]{3})\s+(\d{1,2})\s+TIL\s+(\d{1,2})', data_part)

                try:
                    y = dt_b.year
                    if match_full:
                        m1, d1, m2, d2 = match_full.groups()
                        ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                        fim_dt = datetime.strptime(f"{y} {m2} {d2}", "%Y %b %d")
                    elif match_partial:
                        m1, d1, d2 = match_partial.groups()
                        ini_dt = datetime.strptime(f"{y} {m1} {d1}", "%Y %b %d")
                        # Usa o mesmo mês do início
                        fim_dt = datetime.strptime(f"{y} {m1} {d2}", "%Y %b %d")
                    
                    if ini_dt and fim_dt:
                        if fim_dt < ini_dt: fim_dt = fim_dt.replace(year=y+1)
                        
                        # Gera os dias
                        curr = ini_dt
                        while curr <= fim_dt:
                            # SE houver filtro de dias, respeita. SE NÃO houver, pega todos.
                            if not dias_filtro or curr.weekday() in dias_filtro:
                                slots = extrair_horarios(hora_txt, curr, icao)
                                resultado_final.extend(slots)
                            curr += timedelta(days=1)
                except:
                    pass
            
            # Se conseguiu processar blocos, retorna (evita conflito com lógicas abaixo)
            if resultado_final: return resultado_final

    # ==========================================================================
    # ABAIXO: LÓGICAS ANTIGAS (FALLBACK PARA PADRÕES SIMPLES)
    # ==========================================================================

    # CASO: DATA ESPECÍFICA + RANGE SEM MÊS (Correção SBBR antiga)
    match_composto = re.match(r'^([A-Z]{3}\s+\d{1,2}\s+.*?)\s+(\d{1,2}\s+TIL\s+[A-Z]{3}.*)', text)
    if match_composto:
        parte_1 = match_composto.group(1)
        parte_2 = match_composto.group(2)
        mes_vigencia = dt_b.strftime("%b").upper()
        text = f"{parte_1} {mes_vigencia} {parte_2}"

    # CASO: DLY
    if "DLY" in text or "DAILY" in text:
        horarios_str = text.replace("DLY", "").replace("DAILY", "").strip()
        dias_exc = []
        if "EXC" in horarios_str:
            parts = horarios_str.split("EXC")
            horarios_str = parts[0].strip()
            exc_text = parts[1].strip()
            for k, v in week_map.items():
                if k in exc_text: dias_exc.append(v)

        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() in dias_exc:
                curr += timedelta(days=1)
                continue
            slots = extrair_horarios(horarios_str, curr, icao)
            resultado_final.extend(slots)
            curr += timedelta(days=1)
        if resultado_final: return resultado_final

    # CASO: MON TIL FRI
    match_week_range = re.search(r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)', text)
    if match_week_range:
        start_idx = week_map[match_week_range.group(1)]
        end_idx = week_map[match_week_range.group(2)]
        if start_idx <= end_idx: dias_validos = list(range(start_idx, end_idx + 1))
        else: dias_validos = list(range(start_idx, 7)) + list(range(0, end_idx + 1))
        horario_txt = text.replace(match_week_range.group(0), "").strip()
        
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() in dias_validos:
                slots = extrair_horarios(horario_txt, curr, icao)
                resultado_final.extend(slots)
            curr += timedelta(days=1)
        if resultado_final: return resultado_final

    # CASO: MON WED FRI
    if any(d in text for d in week_map.keys()) and not "TIL" in text:
        dias_alvo = set()
        for k, v in week_map.items():
            if k in text: dias_alvo.add(v)
        horario_txt = text
        for d in week_map.keys(): horario_txt = horario_txt.replace(d, "")
        
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() in dias_alvo:
                slots = extrair_horarios(horario_txt, curr, icao)
                resultado_final.extend(slots)
            curr += timedelta(days=1)
        if resultado_final: return resultado_final

    # CASO: RANGES DATAS (JAN 01 TIL FEB 15) - Lógica Genérica
    if "TIL" in text:
        pattern_full = r'([A-Z]{3}\s+\d{1,2})\s+TIL\s+([A-Z]{3}\s+\d{1,2})'
        matches = re.finditer(pattern_full, text)
        found_any = False
        for m in matches:
            found_any = True
            inicio_str, fim_str = m.group(1), m.group(2)
            horario_raw = re.sub(pattern_full, "", text).strip()
            horario_raw = re.sub(r'[A-Z]{3}\s+\d{1,2}', "", horario_raw).replace("TIL", "").strip()
            try:
                y = dt_b.year
                ini_dt = datetime.strptime(f"{y} {inicio_str}", "%Y %b %d")
                fim_dt = datetime.strptime(f"{y} {fim_str}", "%Y %b %d")
                if fim_dt < ini_dt: fim_dt = fim_dt.replace(year=y+1)
                curr = ini_dt
                while curr <= fim_dt:
                    slots = extrair_horarios(horario_raw, curr, icao)
                    resultado_final.extend(slots)
                    curr += timedelta(days=1)
            except: pass
        if found_any: return resultado_final

    return resultado_final