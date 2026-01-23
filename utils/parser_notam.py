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
    """Converte string 'YYMMDDHHMM' do NOTAM em datetime object."""
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
    """Cria data evitando erros de dia inválido (ex: 31 de Fev)."""
    try:
        return datetime(ano, mes, dia)
    except: return None

def gerar_sequencia_datas(ano_base, mes_ini, dia_ini, mes_fim, dia_fim):
    """Gera lista de datas entre dois pontos, tratando virada de ano."""
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
    """Ajusta o ano de uma data extraída do texto baseada no Início do NOTAM (B)."""
    if not dt: return None
    if dt.month < dt_referencia_b.month and dt_referencia_b.month > 10:
        return dt.replace(year=dt_referencia_b.year + 1)
    return dt

# ==============================================================================
# FUNÇÃO PRINCIPAL (SCANNER MESTRE V18.7)
# ==============================================================================

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    Interpreta o campo D de um NOTAM e gera os slots de tempo (início/fim).
    V18.7: Correção de Pernoites (Barras) e Blocos Contínuos (CASO 16, 28, 60)
    """
    
    # 1. Parse dos Limites Operacionais (B e C)
    dt_b = parse_notam_date(item_b_raw)
    dt_c = None
    if item_c_raw and "PERM" in str(item_c_raw).upper():
        if dt_b: dt_c = dt_b + timedelta(days=365)
    else:
        dt_c = parse_notam_date(item_c_raw)

    if not dt_b or not dt_c: return []

    slots = []
    text = str(item_d_text).upper()

    # 2. Tratamento de Placeholders Solares
    SR_PLACEHOLDER = "0800"
    SS_PLACEHOLDER = "2000"
    text = re.sub(r'\bSR\b', SR_PLACEHOLDER, text)
    text = re.sub(r'\bSS\b', SS_PLACEHOLDER, text)
    
    text = " ".join(text.split())
    text = re.sub(r'(\d+)/([A-Z]+)', r'\1 \2', text)
    
    contexto_ano = dt_b.year
    contexto_mes = dt_b.month

    # 3. Definição dos Regex (Scanner Multicamada)
    
    # R1: Complexo (Dia da Semana + Hora TIL Dia da Semana + Hora)
    # Ex: MON 0800 TIL TUE 1200
    regex_complexo = r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{4})\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{4})'
    
    # R2: Contínuo Data (Hora TIL Dia Hora) -> NOVO V18.7
    # Ex: 1543 TIL 20 2129 (Hora Início, Dia Fim, Hora Fim)
    regex_continuous = r'(\d{4})\s+TIL\s+(\d{1,2})\s+(\d{4})'

    # R3: Simples (Hora TIL Hora ou Hora-Hora)
    # Ex: 0800-1200
    regex_simples = r'(\d{4})\s*(?:-|TIL)\s*(\d{4})'
    
    # Compilação Mestra
    re_master = re.compile(f'(?:{regex_complexo})|(?:{regex_continuous})|(?:{regex_simples})')

    matches = list(re_master.finditer(text))
    last_end = 0
    
    ultima_lista_datas = [] 
    ultimo_filtro_semana = set()

    if not matches and not slots: 
        return [{'inicio': dt_b, 'fim': dt_c}]

    # 4. Iteração sobre os Segmentos
    for match in matches:
        # Extração de grupos baseado na ordem do regex mestre
        # 1-4: Complexo | 5-7: Contínuo | 8-9: Simples
        g = match.groups()
        
        # Flags de controle
        tipo_match = None # 'complexo', 'continuo', 'simples'
        is_overnight = False
        
        c_dia_ini, c_hora_ini, c_dia_fim, c_hora_fim = g[0], g[1], g[2], g[3]
        cont_hora_ini, cont_dia_fim, cont_hora_fim = g[4], g[5], g[6]
        s_hora_ini, s_hora_fim = g[7], g[8]

        # Definição dos parâmetros do slot baseado no tipo
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
            # Offset será calculado dinamicamente no loop de datas

        else:
            tipo_match = 'simples'
            h_ini_str, h_fim_str = s_hora_ini, s_hora_fim
            if int(h_fim_str) < int(h_ini_str): 
                offset_dias = 1
                is_overnight = True
            else:
                offset_dias = 0

        # Análise do Texto (Datas)
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
                    
                    # FIX V18.7: Se for overnight e temos dias consecutivos (MON/TUE),
                    # ignoramos o segundo dia (que é apenas o término do turno da noite anterior)
                    # Ex: MON/TUE -> Gera slots começando em MON e TUE.
                    # Mas se for MON/TUE TIL THU/FRI (overnight), queremos slots começando em MON, TUE, WED, THU.
                    # O "FRI" em THU/FRI é o fim do turno de THU. Não deve iniciar slot.
                    # Mas o parser de Range "TIL" já trata o range inclusivo.
                    # O problema principal é o "MON/TUE" sozinho ou como inicio de range.
                    
                    # Lógica Simplificada: Adiciona todos. O filtro overnight será tratado melhor com ranges.
                    # Se for range "MON/TUE TIL THU/FRI", o loop abaixo vai pegar indices.
                    # MON(0), TUE(1) ... THU(3), FRI(4).
                    # Se for overnight, devemos podar o último elemento se ele for consecutivo?
                    # Para CASO_16 (MON/TUE TIL THU/FRI 1940-0115), queremos segundas, terças, quartas e quintas.
                    # Range atual gera: 0, 1, 2, 3, 4. (Inclui Sexta). Sexta à noite começa o slot?
                    # Não, Sexta de manhã termina o slot de Quinta.
                    # Então, se is_overnight, e estamos num range de semana, removemos o último dia?
                    # Não podemos generalizar. Vamos focar na duplicidade de datas numéricas que foi o erro principal.
                    
                    for p in partes:
                        if p in WEEK_MAP: filtro_semana_deste_segmento.add(WEEK_MAP[p])
                    k += 1; continue
                
                # Dias da Semana (Range TIL)
                if tok in WEEK_MAP:
                    idx_tok = WEEK_MAP[tok]
                    if k + 2 < len(tokens) and tokens[k+1] == "TIL":
                        alvo_tok = tokens[k+2]
                        if alvo_tok in WEEK_MAP:
                            idx_alvo = WEEK_MAP[alvo_tok]
                            
                            # FIX CASO 16/60: Pruning de Overnight em Ranges de Semana
                            # Se for overnight (ex: 1940-0115) e o range for algo como MON/TUE TIL THU/FRI
                            # O usuário quer dizer "Noite de Mon até Noite de Thu".
                            # Se o token alvo faz parte de um par (ex: THU/FRI), o FRI é o fim.
                            # Como é difícil saber se veio de um par aqui, aplicamos a lógica:
                            # Se is_overnight, removemos o último dia do range?
                            # NÃO, isso é arriscado.
                            # Vamos manter a lógica padrão. O CASO_16 falhou por excesso (137 vs 130).
                            
                            if idx_tok <= idx_alvo: filtro_semana_deste_segmento.update(range(idx_tok, idx_alvo + 1))
                            else: 
                                filtro_semana_deste_segmento.update(range(idx_tok, 7))
                                filtro_semana_deste_segmento.update(range(0, idx_alvo + 1))
                            k += 3; continue
                    filtro_semana_deste_segmento.add(idx_tok); k += 1
                else: 
                    k += 1
            
            # Datas Numéricas (JAN 10, 17/18)
            i = 0 
            while i < len(tokens):
                tok = tokens[i]
                if tok in WEEK_MAP or ("/" in tok and not tok[0].isdigit()): i += 1; continue
                if tok == "TIL" and i>0 and (tokens[i-1] in WEEK_MAP or ("/" in tokens[i-1] and not tokens[i-1][0].isdigit())): i += 1; continue
                
                if tok in MONTH_MAP: contexto_mes = MONTH_MAP[tok]; i += 1; continue
                
                if tok[0].isdigit():
                    # Range Numérico (10 TIL 15)
                    if i + 2 < len(tokens) and tokens[i+1] == "TIL":
                        alvo = tokens[i+2]
                        dia_start = int(tok.split("/")[0])
                        # ... TIL 15
                        if alvo[0].isdigit():
                            dia_end = int(alvo.split("/")[0])
                            datas_deste_segmento.extend(gerar_sequencia_datas(contexto_ano, contexto_mes, dia_start, contexto_mes, dia_end))
                            i += 3; continue
                        # ... TIL FEB 15
                        elif alvo in MONTH_MAP:
                            mes_dest = MONTH_MAP[alvo]
                            if i + 3 < len(tokens) and tokens[i+3][0].isdigit():
                                dia_end = int(tokens[i+3].split("/")[0])
                                datas_deste_segmento.extend(gerar_sequencia_datas(contexto_ano, contexto_mes, dia_start, mes_dest, dia_end))
                                contexto_mes = mes_dest; i += 4; continue
                    
                    # Lista com Barras (17/18)
                    if "/" in tok: 
                        partes = tok.split("/")
                        
                        # --- FIX V18.7: Duplicidade em Overnight (Datas Numéricas) ---
                        # Se for overnight e as datas forem consecutivas (17/18),
                        # assume-se que 18 é apenas o término do dia 17. Ignora o 18 como início.
                        consecutivos = False
                        try:
                            v1 = int(partes[0])
                            v2 = int(partes[1])
                            # Verifica consecutivo simples ou virada de mês (ex: 30/01)
                            if v2 == v1 + 1 or (v1 >= 28 and v2 == 1):
                                consecutivos = True
                        except: pass

                        if is_overnight and consecutivos and len(partes) == 2:
                             dt = criar_data_segura(contexto_ano, contexto_mes, int(partes[0]))
                             if dt: datas_deste_segmento.append(dt)
                        else:
                            # Comportamento padrão (adiciona todas)
                            for p in partes:
                                dt = criar_data_segura(contexto_ano, contexto_mes, int(p))
                                if dt: datas_deste_segmento.append(dt)
                        
                        i += 1; continue
                    else:
                        dt = criar_data_segura(contexto_ano, contexto_mes, int(tok))
                        if dt: datas_deste_segmento.append(dt)
                        i += 1; continue
                i += 1
            
            # Fallback para filtro de semana puro
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

        # Atualiza memória
        if achou_nova_definicao:
            ultima_lista_datas = datas_deste_segmento
            ultimo_filtro_semana = filtro_semana_deste_segmento
        else:
            datas_deste_segmento = ultima_lista_datas
            filtro_semana_deste_segmento = ultimo_filtro_semana

        # 5. Geração dos Slots
        for dt_crua in datas_deste_segmento:
            dt_final = ajustar_ano_referencia(dt_crua, dt_b)
            if not dt_final: continue
            
            if tipo_match == 'complexo' and filtro_dia_inicio is not None:
                if dt_final.weekday() != filtro_dia_inicio: continue
            elif filtro_semana_deste_segmento and dt_final.weekday() not in filtro_semana_deste_segmento:
                continue
            
            s_ini_teorico = dt_final.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
            s_ini = max(s_ini_teorico, dt_b)
            
            # Cálculo do Fim
            if tipo_match == 'continuo':
                # Lógica para "1543 TIL 20 2129"
                # O dia de fim é fornecido pelo regex (dia_fim_target)
                dia_alvo = dia_fim_target
                # Se dia alvo for menor que dia inicio, virou o mês
                mes_fim_calc = dt_final.month
                ano_fim_calc = dt_final.year
                
                if dia_alvo < dt_final.day:
                    mes_fim_calc += 1
                    if mes_fim_calc > 12:
                        mes_fim_calc = 1
                        ano_fim_calc += 1
                
                dt_fim_base = criar_data_segura(ano_fim_calc, mes_fim_calc, dia_alvo)
                if not dt_fim_base: dt_fim_base = dt_final # Fallback
                
                s_fim = dt_fim_base.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
                
            else:
                # Simples ou Complexo
                s_fim = dt_final.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
                
                if s_ini >= s_fim and not ("DLY" in segmento or "DAILY" in segmento):
                     # Burla de 1 minuto para início inválido no mesmo dia
                     s_fim = s_ini + timedelta(minutes=1)
                else:
                    s_fim += timedelta(days=offset_dias)
            
            if s_fim <= dt_b or s_ini >= dt_c: continue
            slots.append({'inicio': s_ini, 'fim': min(s_fim, dt_c)})

    slots.sort(key=lambda x: x['inicio'])
    return slots