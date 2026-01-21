import re
from datetime import datetime, timedelta

def parse_notam_date(date_str):
    """Converte string YYMMDDHHMM em datetime object"""
    try:
        if not date_str or len(str(date_str)) != 10:
            return None
        return datetime.strptime(str(date_str), "%y%m%d%H%M")
    except:
        return None

def calculate_sun_times(date_obj, lat, lon):
    """
    Versão SIMPLIFICADA (Sem biblioteca externa para evitar erros).
    Assume SR=06:00 e SS=18:00 locais aproximados para teste.
    """
    sr = date_obj.replace(hour=9, minute=0, second=0)  # ~06:00 Local
    ss = date_obj.replace(hour=21, minute=0, second=0) # ~18:00 Local
    return sr, ss

def get_coords_from_icao(icao):
    return (-23.4356, -46.4731) # Default genérico

def extrair_horarios(texto_horario, base_date, icao):
    """
    Lê strings de hora: '1000-1500', 'SR-SS', '2200-0500'
    """
    slots = []
    # Remove lixo comum em horários
    texto_clean = texto_horario.upper().replace("/", "-").replace(" TO ", "-").strip()
    
    # Divide se houver múltiplos horários (ex: 1000-1200 1400-1600)
    partes = re.split(r'\s+AND\s+|\s+', texto_clean)
    
    sr_dt, ss_dt = calculate_sun_times(base_date, 0, 0)

    for parte in partes:
        if "-" not in parte: continue
        try:
            inicio_str, fim_str = parte.split("-")
            
            # Resolve Início
            if "SR" in inicio_str: dt_ini = sr_dt
            elif "SS" in inicio_str: dt_ini = ss_dt
            elif re.match(r'^\d{4}$', inicio_str):
                dt_ini = base_date.replace(hour=int(inicio_str[:2]), minute=int(inicio_str[2:]))
            else: continue

            # Resolve Fim
            if "SR" in fim_str: dt_fim = sr_dt
            elif "SS" in fim_str: dt_fim = ss_dt
            elif re.match(r'^\d{4}$', fim_str):
                dt_fim = base_date.replace(hour=int(fim_str[:2]), minute=int(fim_str[2:]))
                # Tratamento de Madrugada (Inicio 2200 Fim 0500)
                if dt_fim < dt_ini:
                    dt_fim += timedelta(days=1)
            else: continue

            slots.append({'inicio': dt_ini, 'fim': dt_fim})
        except:
            continue
    return slots

def limpar_barras_datas(text):
    """
    Resolve o problema das datas com barra (Pattern A e D).
    Ex: DEC 07/08 -> DEC 07
    Ex: MON/TUE -> MON
    """
    # 1. Datas numéricas: 07/08 -> 07 (Pega só o primeiro dia, o horário cuida do resto)
    text = re.sub(r'(\d{1,2})/\d{1,2}', r'\1', text)
    
    # 2. Dias da semana: MON/TUE -> MON
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    pattern_days = r'(' + '|'.join(days) + r')/(' + '|'.join(days) + r')'
    text = re.sub(pattern_days, r'\1', text)
    
    return text

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    Função Mestre: Processa o Item D e retorna lista de slots.
    """
    if not item_d_text or not item_d_text.strip(): return []

    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    if not dt_b or not dt_c: return []

    resultado_final = []
    
    # --- 1. LIMPEZA E NORMALIZAÇÃO ---
    text = item_d_text.upper().strip()
    text = text.replace('\n', ' ') # Remove quebras de linha (Caso SBPA)
    text = text.replace(',', ' ').replace('.', ' ').replace('  ', ' ')
    
    # Aplica a correção das barras (Fundamental para os erros SBBR, SBGO, SBPL)
    text = limpar_barras_datas(text)
    
    # ==========================================================================
    # CASO: DATA ESPECÍFICA + RANGE (DEC 07 ... 08 TIL JAN 30)
    # ==========================================================================
    # Regex: (MES DIA HORAS) (DIA TIL MES DIA HORAS)
    match_composto = re.match(r'^([A-Z]{3}\s+\d{1,2}\s+.*?)\s+(\d{1,2}\s+TIL\s+[A-Z]{3}.*)', text)
    if match_composto:
        parte_1 = match_composto.group(1)
        parte_2 = match_composto.group(2)
        # Injeta o mês do Item B na parte 2 que ficou sem mês
        mes_vigencia = dt_b.strftime("%b").upper()
        text = f"{parte_1} {mes_vigencia} {parte_2}" # Unifica corrigido para ser processado abaixo

    # ==========================================================================
    # CASO: DIÁRIO (DLY)
    # ==========================================================================
    if "DLY" in text or "DAILY" in text:
        # Extrai horário removendo as palavras chave
        horarios_str = text.replace("DLY", "").replace("DAILY", "").strip()
        
        # Lógica de Exceção (EXC)
        dias_exc = []
        if "EXC" in horarios_str:
            parts = horarios_str.split("EXC")
            horarios_str = parts[0].strip()
            exc_text = parts[1].strip()
            week_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}
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
            
        # Se achou DLY, geralmente é a regra única. Retorna.
        if resultado_final: return resultado_final

    # ==========================================================================
    # CASO: INTERVALO DE DIAS DA SEMANA (MON TIL FRI)
    # ==========================================================================
    week_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}
    
    # Procura padrão "DIA TIL DIA" (Ex: MON TIL FRI)
    match_week_range = re.search(r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)', text)
    
    if match_week_range:
        start_day_name = match_week_range.group(1)
        end_day_name = match_week_range.group(2)
        
        start_idx = week_map[start_day_name]
        end_idx = week_map[end_day_name]
        
        # Gera lista de dias (ex: 0, 1, 2, 3, 4)
        if start_idx <= end_idx:
            dias_validos = list(range(start_idx, end_idx + 1))
        else: # Cruza a semana (Ex: FRI TIL MON -> 4, 5, 6, 0)
            dias_validos = list(range(start_idx, 7)) + list(range(0, end_idx + 1))
            
        # Remove o trecho "MON TIL FRI" para sobrar só o horário
        horario_txt = text.replace(match_week_range.group(0), "").strip()
        
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() in dias_validos:
                slots = extrair_horarios(horario_txt, curr, icao)
                resultado_final.extend(slots)
            curr += timedelta(days=1)
            
        if resultado_final: return resultado_final

    # ==========================================================================
    # CASO: DIAS DA SEMANA SOLTOS (MON WED FRI)
    # ==========================================================================
    if any(d in text for d in week_map.keys()) and not "TIL" in text:
        dias_alvo = set()
        for k, v in week_map.items():
            if k in text: dias_alvo.add(v)
            
        horario_txt = text
        for d in week_map.keys():
            horario_txt = horario_txt.replace(d, "")
            
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() in dias_alvo:
                slots = extrair_horarios(horario_txt, curr, icao)
                resultado_final.extend(slots)
            curr += timedelta(days=1)
            
        if resultado_final: return resultado_final

    # ==========================================================================
    # CASO: INTERVALO DE DATAS (JAN 01 TIL FEB 15)
    # Suporta múltiplos intervalos na mesma string (findall)
    # ==========================================================================
    months_str = "JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC"
    
    # Padrão: MES DIA (opcional) TIL MES DIA (opcional)
    # Ex: DEC 24 TIL JAN 31
    # Ex: 08 TIL JAN 30 (Sem mês inicial, usa do item B/contexto)
    
    # Vamos simplificar: Procura qualquer coisa que pareça "TIL MES DIA"
    if "TIL" in text:
        # Divide por espaços grandes ou palavras chave para tentar isolar blocos
        # Mas para o caso SBFL (DEC 24 TIL JAN 31 FEB 11 TIL 23), melhor estratégia:
        
        # 1. Tenta achar todos os intervalos explícitos
        # Regex: (MES DIA) TIL (MES DIA)
        pattern_full = r'([A-Z]{3}\s+\d{1,2})\s+TIL\s+([A-Z]{3}\s+\d{1,2})'
        matches = re.finditer(pattern_full, text)
        
        found_any = False
        for m in matches:
            found_any = True
            inicio_str = m.group(1) # DEC 24
            fim_str = m.group(2)    # JAN 31
            
            # O horário geralmente está no final do bloco ou no final do texto todo
            # Simplificação: Pega todo o texto que não é data como horário
            horario_raw = re.sub(pattern_full, "", text).strip()
            # Remove datas soltas que sobraram
            horario_raw = re.sub(r'[A-Z]{3}\s+\d{1,2}', "", horario_raw).strip()
            # Remove TIL
            horario_raw = horario_raw.replace("TIL", "").strip()

            try:
                # Converte datas
                y = dt_b.year
                ini_dt = datetime.strptime(f"{y} {inicio_str}", "%Y %b %d")
                fim_dt = datetime.strptime(f"{y} {fim_str}", "%Y %b %d")
                
                # Ajuste de ano (Virada de ano)
                if fim_dt < ini_dt: fim_dt = fim_dt.replace(year=y+1)
                
                # Gera dias
                curr = ini_dt
                while curr <= fim_dt:
                    slots = extrair_horarios(horario_raw, curr, icao)
                    resultado_final.extend(slots)
                    curr += timedelta(days=1)
            except: pass
            
        if found_any: return resultado_final

        # 2. Tenta achar "DIA TIL MES DIA" (Mês implícito no início)
        # Ex: 08 TIL JAN 30 (Do caso SBBR corrigido)
        pattern_partial = r'(\d{1,2})\s+TIL\s+([A-Z]{3}\s+\d{1,2})'
        match_p = re.search(pattern_partial, text)
        
        if match_p:
            dia_ini = match_p.group(1)
            fim_full = match_p.group(2)
            
            # Assume mês de início = mês do Item B
            mes_ini = dt_b.strftime("%b").upper()
            
            horario_raw = re.sub(pattern_partial, "", text).strip()
            horario_raw = re.sub(r'[A-Z]{3}\s+\d{1,2}', "", horario_raw).replace("TIL", "")
            
            try:
                y = dt_b.year
                ini_dt = datetime.strptime(f"{y} {mes_ini} {dia_ini}", "%Y %b %d")
                fim_dt = datetime.strptime(f"{y} {fim_full}", "%Y %b %d")
                
                if fim_dt < ini_dt: fim_dt = fim_dt.replace(year=y+1)
                
                curr = ini_dt
                while curr <= fim_dt:
                    slots = extrair_horarios(horario_raw, curr, icao)
                    resultado_final.extend(slots)
                    curr += timedelta(days=1)
                return resultado_final
            except: pass

    # ==========================================================================
    # CASO: LISTA DE DATAS (JAN 17 18 20)
    # ==========================================================================
    for mon in months_str.split("|"):
        if mon in text:
            try:
                # Pega trecho a partir do mês
                idx = text.find(mon)
                subs = text[idx:]
                tokens = subs.split()
                
                dias = []
                horario_tokens = []
                
                for t in tokens[1:]:
                    if t.isdigit() and len(t) <= 2: dias.append(int(t))
                    else: horario_tokens.append(t)
                
                horario_txt = " ".join(horario_tokens)
                if not horario_txt: continue
                
                mes_obj = datetime.strptime(mon, "%b")
                
                for d in dias:
                    dt_base = datetime(dt_b.year, mes_obj.month, d)
                    # Se data muito anterior ao inicio, pode ser ano seguinte? (Refinamento futuro)
                    slots = extrair_horarios(horario_txt, dt_base, icao)
                    resultado_final.extend(slots)
                    
                if resultado_final: return resultado_final
            except: pass

    return resultado_final