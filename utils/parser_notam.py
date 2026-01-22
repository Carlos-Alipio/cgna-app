import re
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES ---
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
        clean_str = str(date_str).replace("-", "").replace(":", "").replace(" ", "").strip()
        if len(clean_str) == 10:
            return datetime.strptime(clean_str, "%y%m%d%H%M")
        elif len(clean_str) == 12:
            return datetime.strptime(clean_str, "%Y%m%d%H%M")
        return None
    except: return None

def criar_data_segura(ano, mes, dia):
    try:
        return datetime(ano, mes, dia)
    except: return None

def gerar_sequencia_datas(ano_base, mes_ini, dia_ini, mes_fim, dia_fim):
    datas = []
    dt_start = criar_data_segura(ano_base, mes_ini, dia_ini)
    dt_end = criar_data_segura(ano_base, mes_fim, dia_fim)
    
    if not dt_start or not dt_end: return []
    
    if dt_end < dt_start:
        dt_end = dt_end.replace(year=ano_base + 1)
        
    curr = dt_start
    while curr <= dt_end:
        datas.append(curr)
        curr += timedelta(days=1)
    return datas

def ajustar_ano_referencia(dt, dt_referencia_b):
    if not dt: return None
    if dt.month < dt_referencia_b.month and dt_referencia_b.month > 10:
        return dt.replace(year=dt_referencia_b.year + 1)
    return dt

def resolver_dia_semana_composto(token):
    if "/" in token:
        partes = token.split("/")
        if partes[0] in WEEK_MAP:
            return WEEK_MAP[partes[0]]
    if token in WEEK_MAP:
        return WEEK_MAP[token]
    return None

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    V14: Correção de Precedência DLY. Datas explícitas (JAN 06) vencem DLY genérico.
    """
    dt_b = parse_notam_date(item_b_raw)
    
    # Tratamento para PERM
    dt_c = None
    if item_c_raw and "PERM" in str(item_c_raw).upper():
        if dt_b:
            dt_c = dt_b + timedelta(days=365)
    else:
        dt_c = parse_notam_date(item_c_raw)

    if not dt_b or not dt_c: return []

    slots = []
    text = str(item_d_text).upper().strip() if item_d_text else ""
    
    re_horario = re.compile(r'(\d{4})-(\d{4})')
    matches = list(re_horario.finditer(text))
    
    last_end = 0
    contexto_ano = dt_b.year
    contexto_mes = dt_b.month
    
    ultima_lista_datas = [] 
    ultimo_filtro_semana = set()

    if not matches:
        return [{'inicio': dt_b, 'fim': dt_c}]

    for match in matches:
        h_ini_str, h_fim_str = match.groups()
        segmento = text[last_end:match.start()]
        last_end = match.end()
        
        cruza_noite = int(h_fim_str) < int(h_ini_str)
        
        datas_deste_segmento = []
        filtro_semana_deste_segmento = set()
        achou_nova_definicao = False

        # Tokenização Inicial
        tokens = re.findall(r'[A-Z]+(?:/[A-Z]+)?|\d+(?:/\d+)?', segmento)
        tokens = [t for t in tokens if len(t) > 1 or t.isdigit()]

        tem_conteudo_data = any(t in MONTH_MAP or t[0].isdigit() for t in tokens)
        tem_conteudo_semana = any(t.split("/")[0] in WEEK_MAP for t in tokens)
        
        # --- LÓGICA V14: Prioridade para Datas Específicas ---
        if tem_conteudo_data or tem_conteudo_semana:
            achou_nova_definicao = True
            
            # 1. SCANNER SEMANA
            k = 0
            while k < len(tokens):
                tok = tokens[k]
                idx_tok = resolver_dia_semana_composto(tok)
                
                if idx_tok is not None:
                    if k + 2 < len(tokens) and tokens[k+1] == "TIL":
                        idx_alvo = resolver_dia_semana_composto(tokens[k+2])
                        if idx_alvo is not None:
                            if idx_tok <= idx_alvo:
                                filtro_semana_deste_segmento.update(range(idx_tok, idx_alvo + 1))
                            else:
                                filtro_semana_deste_segmento.update(range(idx_tok, 7))
                                filtro_semana_deste_segmento.update(range(0, idx_alvo + 1))
                            k += 3
                            continue
                    filtro_semana_deste_segmento.add(idx_tok)
                    k += 1
                else:
                    k += 1
            
            # 2. SCANNER DATAS
            i = 0
            while i < len(tokens):
                tok = tokens[i]
                if tok in MONTH_MAP:
                    contexto_mes = MONTH_MAP[tok]
                    i += 1
                    continue
                if resolver_dia_semana_composto(tok) is not None or (tok == "TIL" and i>0 and resolver_dia_semana_composto(tokens[i-1]) is not None):
                    i += 1
                    continue

                if tok[0].isdigit():
                    if "/" in tok:
                        partes = tok.split("/")
                        dia_start, dia_extra = int(partes[0]), int(partes[1])
                        dt = criar_data_segura(contexto_ano, contexto_mes, dia_start)
                        if dt: datas_deste_segmento.append(dt)
                        if not cruza_noite:
                            dt2 = criar_data_segura(contexto_ano, contexto_mes, dia_extra)
                            if dt2: datas_deste_segmento.append(dt2)
                        i += 1
                        continue

                    dia_start = int(tok)
                    if i + 2 < len(tokens) and tokens[i+1] == "TIL":
                        alvo = tokens[i+2]
                        if alvo.isdigit():
                            dia_end = int(alvo)
                            lista = gerar_sequencia_datas(contexto_ano, contexto_mes, dia_start, contexto_mes, dia_end)
                            datas_deste_segmento.extend(lista)
                            i += 3
                            continue
                        elif alvo in MONTH_MAP:
                            mes_dest = MONTH_MAP[alvo]
                            if i + 3 < len(tokens) and tokens[i+3].isdigit():
                                dia_dest = int(tokens[i+3])
                                lista = gerar_sequencia_datas(contexto_ano, contexto_mes, dia_start, mes_dest, dia_dest)
                                datas_deste_segmento.extend(lista)
                                contexto_mes = mes_dest
                                i += 4
                                continue
                    
                    dt = criar_data_segura(contexto_ano, contexto_mes, dia_start)
                    if dt: datas_deste_segmento.append(dt)
                    i += 1
                    continue
                i += 1
            
            # Herança Híbrida (Só dias mudaram, mantém datas)
            if not datas_deste_segmento and ultima_lista_datas:
                datas_deste_segmento = list(ultima_lista_datas)

        # --- SE NÃO ACHOU DATAS ESPECÍFICAS, MAS TEM 'DLY' ---
        elif "DLY" in segmento or "DAILY" in segmento:
            curr = dt_b
            while curr <= dt_c:
                datas_deste_segmento.append(curr)
                curr += timedelta(days=1)
            achou_nova_definicao = True
        
        # --- ATUALIZAÇÃO DA MEMÓRIA ---
        if achou_nova_definicao:
            ultima_lista_datas = datas_deste_segmento
            ultimo_filtro_semana = filtro_semana_deste_segmento
        else:
            datas_deste_segmento = ultima_lista_datas
            filtro_semana_deste_segmento = ultimo_filtro_semana

        # --- GERAÇÃO FINAL ---
        for dt_crua in datas_deste_segmento:
            dt_final = ajustar_ano_referencia(dt_crua, dt_b)
            if not dt_final: continue

            if filtro_semana_deste_segmento and dt_final.weekday() not in filtro_semana_deste_segmento:
                continue
            
            s_ini = dt_final.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
            s_fim = dt_final.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
            if s_fim < s_ini: s_fim += timedelta(days=1)
            
            if s_fim < dt_b or s_ini > dt_c:
                continue
            
            slots.append({'inicio': s_ini, 'fim': s_fim})

    slots.sort(key=lambda x: x['inicio'])
    return slots