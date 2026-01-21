import re
from datetime import datetime, timedelta, time

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
    Versão SIMPLIFICADA (Sem biblioteca externa).
    Assume horários fixos para evitar erro de importação durante os testes.
    Em produção, adicionar 'ephem' no requirements.txt para precisão.
    """
    # Nascer do sol fictício: 06:00 LT (aproximado para UTC dependendo da época)
    # Pôr do sol fictício: 18:00 LT
    # Como o NOTAM é UTC, vamos assumir SR=0900Z e SS=2100Z (média Brasil) para teste
    sr = date_obj.replace(hour=9, minute=0, second=0)
    ss = date_obj.replace(hour=21, minute=0, second=0)
    return sr, ss

def get_coords_from_icao(icao):
    """Retorna lat/lon aproximados (Apenas placeholder nesta versão)"""
    return (-23.4356, -46.4731) 

def is_holiday(date_obj):
    """Verificação simples de feriados (expansível)"""
    feriados = [
        (1, 1), (21, 4), (1, 5), (7, 9), (12, 10), (2, 11), (15, 11), (25, 12)
    ]
    return (date_obj.day, date_obj.month) in feriados

def extrair_horarios(texto_horario, base_date, icao):
    """
    Interpreta strings de hora como:
    '1000-1500', '1000/1500', 'SR-SS', '1200-SS', 'SR-1600'
    Retorna lista de tuplas (datetime_ini, datetime_fim)
    """
    slots = []
    
    # Normaliza separadores e remove espaços extras
    texto_clean = texto_horario.upper().replace("/", "-").replace(" TO ", "-").strip()
    
    # Separa múltiplos horários no mesmo dia
    partes = re.split(r'\s+AND\s+|\s+', texto_clean)
    
    # Chama função simplificada de sol
    sr_dt, ss_dt = calculate_sun_times(base_date, 0, 0)

    for parte in partes:
        if "-" not in parte: continue
        
        try:
            inicio_str, fim_str = parte.split("-")
            
            # Resolve Início
            if "SR" in inicio_str:
                dt_ini = sr_dt
            elif "SS" in inicio_str:
                dt_ini = ss_dt
            elif re.match(r'\d{4}', inicio_str):
                h = int(inicio_str[:2])
                m = int(inicio_str[2:])
                dt_ini = base_date.replace(hour=h, minute=m, second=0)
            else:
                continue # Ignora lixo

            # Resolve Fim
            if "SR" in fim_str:
                dt_fim = sr_dt
            elif "SS" in fim_str:
                dt_fim = ss_dt
            elif re.match(r'\d{4}', fim_str):
                h = int(fim_str[:2])
                m = int(fim_str[2:])
                dt_fim = base_date.replace(hour=h, minute=m, second=0)
                
                # Se hora fim < hora inicio (ex: 2200-0500), soma 1 dia
                if dt_fim < dt_ini:
                    dt_fim += timedelta(days=1)
            else:
                continue

            slots.append({'inicio': dt_ini, 'fim': dt_fim})
            
        except Exception:
            continue
            
    return slots

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    Função Mestre: Recebe o texto livre (Item D) e retorna lista de slots.
    """
    if not item_d_text or item_d_text.strip() == "":
        return []

    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    
    if not dt_b or not dt_c:
        return []

    resultado_final = []
    text = item_d_text.upper().strip()
    
    # Normalização Inicial
    text = text.replace(",", " ").replace(".", " ").replace("  ", " ")
    
    # ==========================================================================
    # CORREÇÃO DO ERRO (MANTIDA AQUI): "DATA ESPECÍFICA + RANGE SEM MÊS"
    # Detecta padrão: (MES DIA HORARIO) (DIA TIL MES ...)
    # ==========================================================================
    match_composto = re.match(r'^([A-Z]{3}\s+\d{1,2}\s+.*?)\s+(\d{1,2}\s+TIL\s+[A-Z]{3}.*)', text)
    
    if match_composto:
        parte_1 = match_composto.group(1) 
        parte_2 = match_composto.group(2) 
        
        # Injeta o mês do Item B na parte 2
        mes_vigencia = dt_b.strftime("%b").upper()
        parte_2_corrigida = f"{mes_vigencia} {parte_2}"
        
        # Recursividade
        res_1 = interpretar_periodo_atividade(parte_1, icao, item_b_raw, item_c_raw)
        res_2 = interpretar_periodo_atividade(parte_2_corrigida, icao, item_b_raw, item_c_raw)
        
        return res_1 + res_2

    # ==========================================================================
    # 1. PADRÃO: DIÁRIO (DLY ou DAILY)
    # ==========================================================================
    if text.startswith("DLY") or text.startswith("DAILY"):
        horarios_str = text.replace("DLY", "").replace("DAILY", "").strip()
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
            slots_dia = extrair_horarios(horarios_str, curr, icao)
            resultado_final.extend(slots_dia)
            curr += timedelta(days=1)
        return resultado_final

    # ==========================================================================
    # 2. PADRÃO: DIAS DA SEMANA
    # ==========================================================================
    dias_semana_map = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4, "SAT":5, "SUN":6}
    dias_alvo = set()
    tem_dia_semana = any(d in text for d in dias_semana_map.keys())
    
    if tem_dia_semana and "TIL" not in text and not re.search(r'\d{2} TIL', text): 
        for k, v in dias_semana_map.items():
            if k in text: dias_alvo.add(v)
        
        horario_limpo = text
        for d in dias_semana_map.keys():
            horario_limpo = horario_limpo.replace(d, "")
        
        curr = dt_b
        while curr <= dt_c:
            if curr.weekday() in dias_alvo:
                slots_dia = extrair_horarios(horario_limpo, curr, icao)
                resultado_final.extend(slots_dia)
            curr += timedelta(days=1)
        return resultado_final

    # ==========================================================================
    # 3. PADRÃO: RANGES (JAN 01 TIL MAR 15)
    # ==========================================================================
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    
    if "TIL" in text:
        parts = text.split("TIL")
        if len(parts) >= 2:
            inicio_part = parts[0].strip()
            fim_part_full = parts[1].strip()
            
            match_ini = re.search(r'([A-Z]{3})\s+(\d{1,2})$', inicio_part)
            match_fim = re.search(r'^([A-Z]{3})\s+(\d{1,2})', fim_part_full)
            
            if match_ini and match_fim:
                m_ini, d_ini = match_ini.groups()
                m_fim, d_fim = match_fim.groups()
                
                horario_txt = fim_part_full.replace(f"{m_fim} {d_fim}", "").strip()
                
                try:
                    y = dt_b.year
                    mi = datetime.strptime(m_ini, "%b").month
                    mf = datetime.strptime(m_fim, "%b").month
                    
                    start_date = datetime(y, mi, int(d_ini))
                    end_date = datetime(y, mf, int(d_fim))
                    
                    if end_date < start_date:
                        end_date = end_date.replace(year=y+1)
                        
                    curr = start_date
                    while curr <= end_date:
                        slots_dia = extrair_horarios(horario_txt, curr, icao)
                        resultado_final.extend(slots_dia)
                        curr += timedelta(days=1)
                    return resultado_final
                except ValueError:
                    pass

    # ==========================================================================
    # 4. PADRÃO: LISTA DE DATAS (SEP 05 08 12)
    # ==========================================================================
    for mon in months:
        if mon in text:
            try:
                subs = text[text.find(mon):]
                tokens = subs.split()
                dias_encontrados = []
                horario_tokens = []
                
                for token in tokens[1:]:
                    if token.isdigit() and len(token) <= 2:
                        dias_encontrados.append(int(token))
                    else:
                        horario_tokens.append(token)
                
                horario_final = " ".join(horario_tokens)
                if not horario_final: continue 

                mes_idx = datetime.strptime(mon, "%b").month
                year = dt_b.year
                
                for d in dias_encontrados:
                    try:
                        data_base = datetime(year, mes_idx, d)
                        slots = extrair_horarios(horario_final, data_base, icao)
                        resultado_final.extend(slots)
                    except:
                        pass
                
                if resultado_final:
                    return resultado_final
            except:
                pass

    return resultado_final