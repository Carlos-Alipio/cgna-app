import re
from datetime import datetime, timedelta

# --- MAPEAMENTOS GLOBAIS ---
MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    "FEV": 2, "ABR": 4, "MAI": 5, "AGO": 8, "SET": 9, "OUT": 10, "DEZ": 12
}

WEEK_MAP = {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6,
    "SEG": 0, "TER": 1, "QUA": 2, "QUI": 3, "SEX": 4, "SAB": 5, "DOM": 6
}

def parse_notam_date(date_str):
    try:
        if not date_str: return None
        clean_str = ''.join(filter(str.isdigit, str(date_str)))
        if len(clean_str) == 10: return datetime.strptime(clean_str, "%y%m%d%H%M")
        elif len(clean_str) == 12: return datetime.strptime(clean_str, "%Y%m%d%H%M")
        return None
    except: return None

def criar_data_segura(ano, mes, dia):
    try: return datetime(ano, mes, dia)
    except: return None

def ajustar_ano_referencia(dt, dt_b):
    if not dt: return None
    # Se o mês da data for menor que o mês de início (B) e B for fim de ano (Nov/Dez)
    if dt.month < dt_b.month and dt_b.month >= 11:
        return dt.replace(year=dt_b.year + 1)
    return dt.replace(year=dt_b.year)

def gerar_sequencia_datas(ano, mes_ini, dia_ini, mes_fim, dia_fim, dt_b):
    datas = []
    d1 = ajustar_ano_referencia(datetime(ano, mes_ini, dia_ini), dt_b)
    d2 = ajustar_ano_referencia(datetime(ano, mes_fim, dia_fim), dt_b)
    if d2 < d1: d2 = d2.replace(year=d2.year + 1)
    
    curr = d1
    while curr <= d2:
        datas.append(curr)
        curr += timedelta(days=1)
    return datas

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw) if item_c_raw and "PERM" not in str(item_c_raw).upper() else None
    if not dt_b: return []
    if not dt_c: dt_c = dt_b + timedelta(days=365)

    # --- 1. NORMALIZAÇÃO ---
    text = str(item_d_text).upper()
    text = re.sub(r'(\d+)/(\d+)', r'\1 \2', text) # "03/04" -> "03 04"
    text = re.sub(r'(\d+)/([A-Z]+)', r'\1 \2', text) # "30/DEC" -> "30 DEC"
    text = " ".join(text.split())

    # --- 2. SEGMENTAÇÃO POR ÂNCORAS (A alma da V19.0) ---
    # Identifica horários fixos ou intervalos TIL como fim de uma regra
    regex_ancora = r'(\d{4}\s*-\s*\d{4}|\d{4}\s+TIL\s+(?:[A-Z]{3}\s+)?\d{1,2}\s+\d{4}|\d{4}\s+TIL\s+\d{4})'
    partes = re.split(regex_ancora, text)
    
    blocos = []
    for i in range(0, len(partes)-1, 2):
        blocos.append((partes[i] + partes[i+1]).strip())
    if len(partes) % 2 != 0 and partes[-1].strip():
        blocos.append(partes[-1].strip())

    slots = []
    ctx_mes = dt_b.month
    ctx_ano = dt_b.year
    ultima_lista_datas = []
    ultimo_filtro_semana = set()

    # --- 3. PROCESSAMENTO DE BLOCO ISOLADO ---
    for bloco in blocos:
        tokens = re.findall(r'[A-Z]{3}|\d{4}|\d{1,2}|TIL', bloco)
        
        # Identifica Horário do bloco (sempre os dois últimos números de 4 dígitos)
        horarios = re.findall(r'\d{4}', bloco)
        if len(horarios) < 2: continue
        h_ini_str, h_fim_str = horarios[-2], horarios[-1]
        
        # Identifica meses e dias
        dias_bloco = []
        filtro_semana = set()
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t in MONTH_MAP:
                ctx_mes = MONTH_MAP[t]
            elif t in WEEK_MAP:
                filtro_semana.add(WEEK_MAP[t])
            elif t.isdigit() and len(t) <= 2:
                dia = int(t)
                # Verifica TIL (Ex: 05 TIL 08)
                if i + 2 < len(tokens) and tokens[i+1] == 'TIL' and tokens[i+2].isdigit() and len(tokens[i+2]) <= 2:
                    dia_fim = int(tokens[i+2])
                    dias_bloco.extend(gerar_sequencia_datas(ctx_ano, ctx_mes, dia, ctx_mes, dia_fim, dt_b))
                    i += 2
                # Verifica TIL entre meses (Ex: 31 TIL JAN 01)
                elif i + 3 < len(tokens) and tokens[i+1] == 'TIL' and tokens[i+2] in MONTH_MAP:
                    mes_dest = MONTH_MAP[tokens[i+2]]
                    dia_dest = int(tokens[i+3])
                    dias_bloco.extend(gerar_sequencia_datas(ctx_ano, ctx_mes, dia, mes_dest, dia_dest, dt_b))
                    ctx_mes = mes_dest
                    i += 3
                else:
                    dt_gen = criar_data_segura(ctx_ano, ctx_mes, dia)
                    if dt_gen: dias_bloco.append(ajustar_ano_referencia(dt_gen, dt_b))
            i += 1

        # Herança de contexto
        if not dias_bloco and ultima_lista_datas: dias_bloco = ultima_lista_datas
        if not filtro_semana and ultimo_filtro_semana: filtro_semana = ultimo_filtro_semana
        
        if dias_bloco:
            ultima_lista_datas = dias_bloco
            ultimo_filtro_semana = filtro_semana

        # --- 4. GERAÇÃO DE SLOTS DO BLOCO ---
        for d in dias_bloco:
            if filtro_semana and d.weekday() not in filtro_semana: continue
            
            # Cálculo de Overnight
            offset_overnight = 1 if int(h_fim_str) < int(h_ini_str) else 0
            # Especial: Caso o texto use TIL entre horários (Ex: 0610 TIL 0415)
            if "TIL" in bloco and len(horarios) >= 2:
                # Se o bloco for um range contínuo (Ex: 27 2022 TIL 28 0415)
                # O offset deve ser calculado pela diferença de dias entre as datas citadas
                pass # A lógica de sequencia_datas já cuida disso se for o caso

            s_ini = d.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
            s_fim = (d + timedelta(days=offset_overnight)).replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
            
            # Validação contra Limites
            if s_fim <= dt_b or s_ini >= dt_c: continue
            slots.append({'inicio': max(s_ini, dt_b), 'fim': min(s_fim, dt_c)})

    # --- 5. LIMPEZA FINAL ---
    # Remove duplicatas e ordena
    slots_unicos = []
    vistos = set()
    for s in sorted(slots, key=lambda x: x['inicio']):
        chave = (s['inicio'], s['fim'])
        if chave not in vistos:
            slots_unicos.append(s)
            vistos.add(chave)
            
    return slots_unicos