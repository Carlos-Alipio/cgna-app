import re
import math
from datetime import datetime, timedelta
import calendar

# ==============================================================================
# 1. DATABASE GEO (OFFLINE)
# ==============================================================================
AIRPORT_DB = {
    'SBGR': (-23.4355, -46.4731), 'SBSP': (-23.6261, -46.6564), 'SBGL': (-22.8089, -43.2436),
    'SBRJ': (-22.9100, -43.1625), 'SBCF': (-19.6244, -43.9719), 'SBKP': (-23.0069, -47.1344),
    'SBPA': (-29.9939, -51.1711), 'SBCT': (-25.5327, -49.1758), 'SBRF': (-8.1264,  -34.9228),
    'SBSV': (-12.9086, -38.3225), 'SBFZ': (-3.7761,  -38.5322), 'SBBE': (-1.3847,  -48.4789),
    'SBBR': (-15.8697, -47.9208), 'SBEG': (-3.0386,  -60.0497)
}

def get_coords_from_db(icao):
    return AIRPORT_DB.get(str(icao).upper().strip())

# ==============================================================================
# 2. UTILITÁRIOS (DATA, SOL, FERIADOS)
# ==============================================================================
def is_holiday(date_obj):
    ano, mes, dia = date_obj.year, date_obj.month, date_obj.day
    fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)]
    if (mes, dia) in fixos: return True
    
    # Páscoa (Meeus/Jones/Butcher)
    a = ano % 19; b = ano // 100; c = ano % 100
    d = b // 4; e = b % 4; f = (b + 8) // 25
    g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month_e = (h + l - 7 * m + 114) // 31
    day_e = ((h + l - 7 * m + 114) % 31) + 1
    dt_pascoa = datetime(ano, month_e, day_e)
    
    for delta in [-47, -2, 60]: # Carnaval, Sexta Santa, Corpus Christi
        fm = dt_pascoa + timedelta(days=delta)
        if fm.month == mes and fm.day == dia: return True
    return False

def calculate_sun_times_utc(date_obj, lat, lon):
    try:
        ZENITH = 90.8333; N = date_obj.timetuple().tm_yday; lngHour = lon / 15.0
        results = []
        for event in ['sunrise', 'sunset']:
            t = N + ((6 - lngHour) / 24) if event == 'sunrise' else N + ((18 - lngHour) / 24)
            M = (0.9856 * t) - 3.289
            L = M + (1.916 * math.sin(math.radians(M))) + (0.020 * math.sin(math.radians(2 * M))) + 282.634
            L = L % 360
            RA = math.degrees(math.atan(0.91764 * math.tan(math.radians(L)))); RA = RA % 360
            RA = RA + ((math.floor(L/90)) * 90 - (math.floor(RA/90)) * 90); RA = RA / 15
            sinDec = 0.39782 * math.sin(math.radians(L)); cosDec = math.cos(math.asin(sinDec))
            cosH = (math.cos(math.radians(ZENITH)) - (sinDec * math.sin(math.radians(lat)))) / (cosDec * math.cos(math.radians(lat)))
            if cosH > 1 or cosH < -1: return ('00:00', '23:59')
            H = (360 - math.degrees(math.acos(cosH))) / 15 if event == 'sunrise' else math.degrees(math.acos(cosH)) / 15
            T = H + RA - (0.06571 * t) - 6.622; UT = (T - lngHour) % 24
            results.append(f"{int(UT):02d}:{int((UT - int(UT)) * 60):02d}")
        return (results[0], results[1])
    except: return ('06:00', '18:00')

def parse_notam_date(raw_str):
    if not raw_str or len(str(raw_str)) < 6: return None
    try:
        s = str(raw_str).strip()
        return datetime(int(s[:2])+2000, int(s[2:4]), int(s[4:6]))
    except: return None

# ==============================================================================
# 3. PARSER LÓGICO DE DATAS
# ==============================================================================
def parse_segment_logic(text_segment, state_ctx):
    mapa_meses = {'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12}
    mapa_semana = {'MON':0,'TUE':1,'WED':2,'THU':3,'FRI':4,'SAT':5,'SUN':6}
    
    curr_mes = state_ctx['mes']; curr_ano = state_ctx['ano']
    ctx_start = state_ctx['range_start']; ctx_end = state_ctx['range_end']

    dias_coletados = []
    weekdays_found = set()
    
    if 'WKDAYS' in text_segment or 'WORKDAYS' in text_segment:
        for d in [0,1,2,3,4]: weekdays_found.add(d)
        text_segment = text_segment.replace('WKDAYS', ' ').replace('WORKDAYS', ' ')

    # --- NOVIDADE: TEOM (The End Of Month) ---
    if 'TEOM' in text_segment:
        # Define fim como último dia do mês atual
        last_day = calendar.monthrange(curr_ano, curr_mes)[1]
        try:
            end = datetime(curr_ano, curr_mes, last_day)
            # Se tivermos um start (hoje ou contexto), criamos o range
            start = datetime(curr_ano, curr_mes, datetime.now().day) # Simplificação
            ctx_start = start; ctx_end = end
            c = start
            while c <= end:
                dias_coletados.append(c); c += timedelta(days=1)
        except: pass
        text_segment = text_segment.replace('TEOM', ' ')

    regex_wk_range = r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)'
    for m in re.finditer(regex_wk_range, text_segment):
        curr = mapa_semana[m.group(1)]; end = mapa_semana[m.group(2)]
        while True:
            weekdays_found.add(curr)
            if curr == end: break
            curr = (curr + 1) % 7
        text_segment = text_segment.replace(m.group(0), ' ')

    for k, v in mapa_semana.items():
        if k in text_segment:
            weekdays_found.add(v); text_segment = text_segment.replace(k, ' ')

    tokens = text_segment.split()
    if not tokens and ctx_start:
        c = ctx_start
        while c <= ctx_end:
            dias_coletados.append(c); c += timedelta(days=1)
    else:
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in mapa_meses:
                nm = mapa_meses[token]
                if nm < curr_mes: curr_ano += 1
                curr_mes = nm
            elif token == 'TIL':
                if dias_coletados and (i+1 < len(tokens)):
                    start = dias_coletados.pop()
                    prox = tokens[i+1]; i += 1
                    end_m = curr_mes; end_y = curr_ano
                    if prox in mapa_meses:
                        end_m = mapa_meses[prox]
                        if end_m < curr_mes: end_y += 1
                        if i+1 < len(tokens): prox = tokens[i+1]; i += 1
                    if prox.isdigit():
                        try:
                            end = datetime(end_y, end_m, int(prox))
                            ctx_start = start; ctx_end = end
                            curr_mes = end_m; curr_ano = end_y
                            c = start
                            while c <= end:
                                dias_coletados.append(c); c += timedelta(days=1)
                        except: pass
            elif token.isdigit():
                try:
                    dt = datetime(curr_ano, curr_mes, int(token))
                    dias_coletados.append(dt)
                except: pass
            i += 1
        
        if not dias_coletados and weekdays_found and ctx_start:
             c = ctx_start
             while c <= ctx_end:
                 dias_coletados.append(c); c += timedelta(days=1)

    new_state = {'mes': curr_mes, 'ano': curr_ano, 'range_start': ctx_start, 'range_end': ctx_end}
    return dias_coletados, weekdays_found, new_state

# ==============================================================================
# 4. FUNÇÃO PRINCIPAL (V24.0 - HJ/HN + ESPAÇOS + TEOM)
# ==============================================================================
def interpretar_periodo_atividade(texto_bruto, icao, item_b_raw, item_c_raw):
    """
    Retorna lista de dicts: [{'inicio': dt, 'fim': dt}, ...]
    """
    if not isinstance(texto_bruto, str) or not texto_bruto: return []

    coords = get_coords_from_db(icao) or (-15.7942, -47.8822)
    lat, lon = coords
    
    dt_notam_ini = parse_notam_date(item_b_raw) or datetime.now()
    dt_notam_fim = parse_notam_date(item_c_raw) or (dt_notam_ini + timedelta(days=30))
    
    texto = texto_bruto.upper().strip()
    for p in [',', '.', ';', ':']: texto = texto.replace(p, ' ')
    texto = texto.replace(' AND ', ' ').replace(' & ', ' ')
    texto = re.sub(r'([A-Z]{3})/([A-Z]{3})', r'\1', texto) 
    texto = re.sub(r'(\d{1,2})/(\d{1,2})', r'\1', texto)
    
    # --- PADRONIZAÇÕES V24 ---
    replacements = {
        '0CT': 'OCT', '1AN': 'JAN', 'SR-SS': 'SR-SS', 'SS-SR': 'SS-SR', 
        'DAILY': 'DLY', 'EXCEPT': 'EXC',
        'HJ': 'SR-SS', 'HN': 'SS-SR' # Traduz ICAO Codes para nosso padrão interno
    } 
    for k, v in replacements.items(): texto = texto.replace(k, v)

    # --- REGEX ROBUSTA V24 (Aceita espaços: 1200 - 1400) ---
    # \d{4} \s* [/-] \s* \d{4}  -> Permite espaços opcionais ao redor do traço/barra
    regex_hora = re.compile(r'(\d{4}\s*[/-]\s*\d{4}|SR-SS|SS-SR|H24)')
    
    matches = list(regex_hora.finditer(texto))
    if not matches: return []

    output_list = [] 
    state = {'ano': dt_notam_ini.year, 'mes': dt_notam_ini.month, 'range_start': None, 'range_end': None, 'cache_dias': []}
    last_end = 0 
    
    for match in matches:
        # Limpa espaços do horário capturado (ex: "1000 - 1200" vira "1000-1200")
        horario_type = match.group(1).replace(' ', '')
        start_idx, end_idx = match.span()
        segmento_texto = texto[last_end:start_idx].strip()
        last_end = end_idx

        dias_finais_slot = []
        if not segmento_texto and state['cache_dias']:
            dias_finais_slot = list(state['cache_dias'])
        else:
            parts = segmento_texto.split('EXC')
            part_in = parts[0].strip()
            part_ex = parts[1].strip() if len(parts) > 1 else ""

            candidatos = []; wk_in = set()
            if 'DLY' in part_in:
                c = dt_notam_ini
                while c <= dt_notam_fim:
                    candidatos.append(c); c += timedelta(days=1)
                part_in = part_in.replace('DLY', ' ')
                _, wk_in, _ = parse_segment_logic(part_in, state)
            else:
                candidatos, wk_in, state = parse_segment_logic(part_in, state)

            proibidos_dates = []; wk_ex = set(); exc_hol = False
            if part_ex:
                if 'HOL' in part_ex:
                    exc_hol = True
                    part_ex = part_ex.replace('HOL', ' ')
                proibidos_dates, wk_ex, _ = parse_segment_logic(part_ex, state)

            candidatos_unicos = sorted(list(set(candidatos)))
            tem_filtro_in = len(wk_in) > 0; tem_filtro_ex = len(wk_ex) > 0
            
            for dt in candidatos_unicos:
                if tem_filtro_in and dt.weekday() not in wk_in: continue
                if dt in proibidos_dates: continue
                if tem_filtro_ex and dt.weekday() in wk_ex: continue
                if exc_hol and is_holiday(dt): continue
                dias_finais_slot.append(dt)

            state['cache_dias'] = dias_finais_slot

        for dt in dias_finais_slot:
            h_ini_str, h_fim_str = "00:00", "23:59"; next_day = False
            
            if re.match(r'\d{4}[/-]\d{4}', horario_type):
                sep = '-' if '-' in horario_type else '/'
                splits = horario_type.split(sep)
                h_ini_str = f"{splits[0][:2]}:{splits[0][2:]}"
                h_fim_str = f"{splits[1][:2]}:{splits[1][2:]}"
                if (int(splits[1][:2]) < int(splits[0][:2])): next_day = True
            elif horario_type == 'SR-SS':
                h_ini_str, h_fim_str = calculate_sun_times_utc(dt, lat, lon)
            elif horario_type == 'SS-SR':
                s1 = calculate_sun_times_utc(dt, lat, lon)
                s2 = calculate_sun_times_utc(dt + timedelta(days=1), lat, lon)
                h_ini_str = s1[1]; h_fim_str = s2[0]
                next_day = True
            elif horario_type == 'H24': pass 

            h_i, m_i = map(int, h_ini_str.split(':'))
            h_f, m_f = map(int, h_fim_str.split(':'))
            dt_inicio = dt.replace(hour=h_i, minute=m_i)
            dt_fim = (dt + timedelta(days=1) if next_day else dt).replace(hour=h_f, minute=m_f)
            
            output_list.append({'inicio': dt_inicio, 'fim': dt_fim})

    return output_list

# ==============================================================================
# TESTER
# ==============================================================================
if __name__ == "__main__":
    print("🛠️ V24 - GOLD VERSION (HJ/HN + Spaces + Output Object)")
    
    txt = "DLY HJ EXC HOL" # Teste de HJ (SR-SS) + Feriado
    icao = "SBGR"
    b = "2512200000" # 20/Dez
    c = "2512302359" # 30/Dez (Tem Natal no meio)
    
    print(f"\nTeste: {txt}")
    res = interpretar_periodo_atividade(txt, icao, b, c)
    
    for r in res:
        print(f"✅ {r['inicio']} -> {r['fim']}")
    
    print("\n(Verifique se dia 25/12 foi pulado e se o horário é do Sol)")