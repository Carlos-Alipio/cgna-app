import re
from datetime import datetime, timedelta

# ==============================================================================
# CONSTANTES E MAPEAMENTOS
# ==============================================================================

MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    "FEV": 2, "ABR": 4, "MAI": 5, "AGO": 8, "SET": 9, "OUT": 10, "DEZ": 12
}

WEEK_MAP = {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6,
    "SEG": 0, "TER": 1, "QUA": 2, "QUI": 3, "SEX": 4, "SAB": 5, "DOM": 6
}

# ==============================================================================
# FUNÇÕES AUXILIARES DE DATA
# ==============================================================================

def parse_notam_date(date_str):
    try:
        if not date_str: return None
        clean_str = ''.join(filter(str.isdigit, str(date_str)))
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
    if dt_end < dt_start: dt_end = dt_end.replace(year=ano_base + 1)
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

# ==============================================================================
# FUNÇÃO PRINCIPAL (V20.0 - FINAL FIX)
# ==============================================================================

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    dt_b = parse_notam_date(item_b_raw)
    dt_c = None
    if item_c_raw and "PERM" in str(item_c_raw).upper():
        if dt_b: dt_c = dt_b + timedelta(days=365)
    else:
        dt_c = parse_notam_date(item_c_raw)

    if not dt_b or not dt_c: return []

    slots = []
    text = str(item_d_text).upper()

    SR_PLACEHOLDER = "0800"
    SS_PLACEHOLDER = "2000"
    text = re.sub(r'\bSR\b', SR_PLACEHOLDER, text)
    text = re.sub(r'\bSS\b', SS_PLACEHOLDER, text)
    
    text = " ".join(text.split())
    text = re.sub(r'(\d+)/([A-Z]+)', r'\1 \2', text)
    
    contexto_ano = dt_b.year
    contexto_mes = dt_b.month

    # Regexes
    regex_complexo = r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{4})\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{4})'
    regex_continuous = r'(\d{4})\s+TIL\s+(\d{1,2})\s+(\d{4})'
    regex_simples = r'(\d{4})\s*(?:-|TIL)\s*(\d{4})'
    
    re_master = re.compile(f'(?:{regex_complexo})|(?:{regex_continuous})|(?:{regex_simples})')

    matches = list(re_master.finditer(text))
    last_end = 0
    ultima_lista_datas = [] 
    ultimo_filtro_semana = set()

    if not matches and not slots: return [{'inicio': dt_b, 'fim': dt_c}]

    for match in matches:
        g = match.groups()
        
        c_dia_ini, c_hora_ini, c_dia_fim, c_hora_fim = g[0], g[1], g[2], g[3]
        cont_hora_ini, cont_dia_fim, cont_hora_fim = g[4], g[5], g[6]
        s_hora_ini, s_hora_fim = g[7], g[8]

        tipo_match = None
        is_overnight = False
        dia_fim_target = None 

        if c_dia_ini:
            tipo_match = 'complexo'
            h_ini_str, h_fim_str = c_hora_ini, c_hora_fim
            idx_ini = WEEK_MAP[c_dia_ini]
            idx_fim = WEEK_MAP[c_dia_fim]
            filtro_dia_inicio = idx_ini 
            if idx_fim >= idx_ini: offset_dias = idx_fim - idx_ini
            else: offset_dias = (7 - idx_ini) + idx_fim
            
        elif cont_hora_ini:
            tipo_match = 'continuo'
            h_ini_str, h_fim_str = cont_hora_ini, cont_hora_fim
            dia_fim_target = int(cont_dia_fim)
            
        else:
            tipo_match = 'simples'
            h_ini_str, h_fim_str = s_hora_ini, s_hora_fim
            if int(h_fim_str) < int(h_ini_str): 
                offset_dias = 1
                is_overnight = True
            else:
                offset_dias = 0

        # Leitura de Datas
        segmento = text[last_end:match.start()]
        last_end = match.end()
        datas_deste_segmento = []
        filtro_semana_deste_segmento = set()
        achou_nova_definicao = False

        tokens = re.findall(r'[A-Za-z0-9/]+', segmento)
        tem_conteudo_data = any(t in MONTH_MAP or t[0].isdigit() for t in tokens)
        tem_conteudo_semana = any(t.split("/")[0] in WEEK_MAP for t in tokens)

        if tem_conteudo_data or tem_conteudo_semana:
            achou_nova_definicao = True
            k = 0 
            while k < len(tokens):
                tok = tokens[k]
                
                # Dias da Semana (MON/TUE)
                if "/" in tok and not tok[0].isdigit():
                    partes = tok.split("/")
                    eh_par_consecutivo = False
                    if len(partes) == 2 and partes[0] in WEEK_MAP and partes[1] in WEEK_MAP:
                        idx0 = WEEK_MAP[partes[0]]
                        idx1 = WEEK_MAP[partes[1]]
                        if idx1 == (idx0 + 1) % 7: eh_par_consecutivo = True

                    # FIX: Poda para Casos 16 e 60
                    if is_overnight and eh_par_consecutivo:
                         filtro_semana_deste_segmento.add(WEEK_MAP[partes[0]])
                    else:
                        for p in partes:
                            if p in WEEK_MAP: filtro_semana_deste_segmento.add(WEEK_MAP[p])
                    k += 1; continue
                
                # Range TIL
                if tok in WEEK_MAP:
                    idx_tok = WEEK_MAP[tok]
                    if k + 2 < len(tokens) and tokens[k+1] == "TIL":
                        alvo_tok = tokens[k+2]
                        if alvo_tok in WEEK_MAP:
                            idx_alvo = WEEK_MAP[alvo_tok]
                            
                            # Tratamento para TIL THU/FRI em Overnight
                            if "/" in alvo_tok:
                                subpartes = alvo_tok.split("/")
                                if subpartes[0] in WEEK_MAP:
                                    idx_alvo = WEEK_MAP[subpartes[0]] # Pega só o primeiro dia do par final
                            
                            if idx_tok <= idx_alvo: filtro_semana_deste_segmento.update(range(idx_tok, idx_alvo + 1))
                            else: 
                                filtro_semana_deste_segmento.update(range(idx_tok, 7))
                                filtro_semana_deste_segmento.update(range(0, idx_alvo + 1))
                            k += 3; continue
                    filtro_semana_deste_segmento.add(idx_tok); k += 1
                else: 
                    k += 1
            
            # Datas Numéricas
            i = 0 
            while i < len(tokens):
                tok = tokens[i]
                if tok in WEEK_MAP or ("/" in tok and not tok[0].isdigit()): i += 1; continue
                if tok == "TIL" and i>0 and (tokens[i-1] in WEEK_MAP or ("/" in tokens[i-1] and not tokens[i-1][0].isdigit())): i += 1; continue
                
                if tok in MONTH_MAP: contexto_mes = MONTH_MAP[tok]; i += 1; continue
                
                if tok[0].isdigit():
                    # Range Numérico
                    if i + 2 < len(tokens) and tokens[i+1] == "TIL":
                        alvo = tokens[i+2]
                        dia_start = int(tok.split("/")[0])
                        if alvo[0].isdigit():
                            dia_end = int(alvo.split("/")[0])
                            datas_deste_segmento.extend(gerar_sequencia_datas(contexto_ano, contexto_mes, dia_start, contexto_mes, dia_end))
                            i += 3; continue
                        elif alvo in MONTH_MAP:
                            mes_dest = MONTH_MAP[alvo]
                            if i + 3 < len(tokens) and tokens[i+3][0].isdigit():
                                dia_end = int(tokens[i+3].split("/")[0])
                                datas_deste_segmento.extend(gerar_sequencia_datas(contexto_ano, contexto_mes, dia_start, mes_dest, dia_end))
                                contexto_mes = mes_dest; i += 4; continue
                    
                    # Lista com Barras
                    if "/" in tok: 
                        partes = tok.split("/")
                        consecutivos = False
                        try:
                            v1 = int(partes[0])
                            v2 = int(partes[1])
                            if v2 == v1 + 1 or (v1 >= 28 and v2 == 1): consecutivos = True
                        except: pass

                        # FIX: Poda para Casos 48-58
                        if is_overnight and consecutivos and len(partes) == 2:
                             dt = criar_data_segura(contexto_ano, contexto_mes, int(partes[0]))
                             if dt: datas_deste_segmento.append(dt)
                        else:
                            for p in partes:
                                dt = criar_data_segura(contexto_ano, contexto_mes, int(p))
                                if dt: datas_deste_segmento.append(dt)
                        i += 1; continue
                    else:
                        dt = criar_data_segura(contexto_ano, contexto_mes, int(tok))
                        if dt: datas_deste_segmento.append(dt)
                        i += 1; continue
                i += 1
            
            # Fallback TUE TIL SAT
            if not datas_deste_segmento and filtro_semana_deste_segmento:
                curr = dt_b
                while curr <= dt_c + timedelta(days=1): 
                    if curr > dt_c: break
                    datas_deste_segmento.append(curr)
                    curr += timedelta(days=1)

            if not datas_deste_segmento and not filtro_semana_deste_segmento and ultima_lista_datas: 
                datas_deste_segmento = list(ultima_lista_datas)

        elif "DLY" in segmento or "DAILY" in segmento:
            curr = dt_b
            while curr <= dt_c: datas_deste_segmento.append(curr); curr += timedelta(days=1)
            achou_nova_definicao = True

        if achou_nova_definicao:
            ultima_lista_datas = datas_deste_segmento
            ultimo_filtro_semana = filtro_semana_deste_segmento
        else:
            datas_deste_segmento = ultima_lista_datas
            filtro_semana_deste_segmento = ultimo_filtro_semana

        # Geração dos Slots
        for dt_crua in datas_deste_segmento:
            dt_final = ajustar_ano_referencia(dt_crua, dt_b)
            if not dt_final: continue
            
            if tipo_match == 'complexo' and filtro_dia_inicio is not None:
                if dt_final.weekday() != filtro_dia_inicio: continue
            elif filtro_semana_deste_segmento and dt_final.weekday() not in filtro_semana_deste_segmento:
                continue
            
            s_ini_teorico = dt_final.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
            s_ini = max(s_ini_teorico, dt_b)
            
            # FIX: Lógica Contínua para Caso 28
            if tipo_match == 'continuo':
                dia_alvo = dia_fim_target
                mes_fim_calc = dt_final.month
                ano_fim_calc = dt_final.year
                
                if dia_alvo < dt_final.day:
                    mes_fim_calc += 1
                    if mes_fim_calc > 12:
                        mes_fim_calc = 1
                        ano_fim_calc += 1
                
                dt_fim_base = criar_data_segura(ano_fim_calc, mes_fim_calc, dia_alvo)
                if not dt_fim_base: dt_fim_base = dt_final 
                
                s_fim = dt_fim_base.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
            
            else:
                s_fim = dt_final.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
                if s_ini >= s_fim and not ("DLY" in segmento or "DAILY" in segmento):
                     s_fim = s_ini + timedelta(minutes=1)
                else:
                    s_fim += timedelta(days=offset_dias)
            
            if s_fim <= dt_b or s_ini >= dt_c: continue
            slots.append({'inicio': s_ini, 'fim': min(s_fim, dt_c)})

    slots.sort(key=lambda x: x['inicio'])
    return slots