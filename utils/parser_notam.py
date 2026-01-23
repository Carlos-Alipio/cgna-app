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
    
    # Se fim for menor que início, assume que virou o ano
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
    # Se a data extraída é JAN e o NOTAM começou em DEZ, provavelmente é ano seguinte
    if dt.month < dt_referencia_b.month and dt_referencia_b.month > 10:
        return dt.replace(year=dt_referencia_b.year + 1)
    # Se a data extraída é DEZ e o NOTAM começou em JAN (retroativo teórico), mantém ano
    # (Lógica simplificada, ajustável conforme necessidade)
    return dt

# ==============================================================================
# FUNÇÃO PRINCIPAL (SCANNER MESTRE V18.6)
# ==============================================================================

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    Interpreta o campo D de um NOTAM e gera os slots de tempo (início/fim).
    
    Versão: 18.6 (Correção Zero Slots + Burla 1 Min + Regex Tolerante)
    """
    
    # 1. Parse dos Limites Operacionais (B e C)
    dt_b = parse_notam_date(item_b_raw)
    dt_c = None
    if item_c_raw and "PERM" in str(item_c_raw).upper():
        if dt_b: dt_c = dt_b + timedelta(days=365) # PERM = 1 ano por padrão
    else:
        dt_c = parse_notam_date(item_c_raw)

    if not dt_b or not dt_c: return []

    slots = []
    text = str(item_d_text).upper()

    # 2. Tratamento de Placeholders Solares (SR/SS)
    # Futuro: Aqui entrará a chamada da API AISWEB para pegar o nascer/pôr do sol real
    SR_PLACEHOLDER = "0800"
    SS_PLACEHOLDER = "2000"
    text = re.sub(r'\bSR\b', SR_PLACEHOLDER, text)
    text = re.sub(r'\bSS\b', SS_PLACEHOLDER, text)
    
    # Limpeza básica
    text = " ".join(text.split())
    # Separa números colados em letras (ex: 20/JAN)
    text = re.sub(r'(\d+)/([A-Z]+)', r'\1 \2', text)
    
    contexto_ano = dt_b.year
    contexto_mes = dt_b.month

    # 3. Definição dos Regex (Scanner)
    
    # Regex Complexo: Dias da semana explícitos (MON 0800 TIL FRI 1200)
    regex_complexo = r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{4})\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{4})'
    
    # Regex Simples: Apenas horários (0800-1200 ou 0800 TIL 1200)
    # V18.6: Adicionado \s* para aceitar espaços (0420 - 0720)
    regex_simples = r'(\d{4})\s*(?:-|TIL)\s*(\d{4})'
    
    re_master = re.compile(f'(?:{regex_complexo})|(?:{regex_simples})')

    matches = list(re_master.finditer(text))
    last_end = 0
    
    # Memória de Contexto (para herança de regras entre segmentos)
    ultima_lista_datas = [] 
    ultimo_filtro_semana = set()

    # Caso Base: Se não achou nenhum horário no texto, assume DLY full-time (B até C)
    if not matches and not slots: 
        return [{'inicio': dt_b, 'fim': dt_c}]

    # 4. Iteração sobre os Segmentos Encontrados
    for match in matches:
        # Grupos do Regex: 1-4 (Complexo), 5-6 (Simples)
        c_dia_ini, c_hora_ini, c_dia_fim, c_hora_fim, s_hora_ini, s_hora_fim = match.groups()
        
        is_complex = (c_dia_ini is not None)
        offset_dias = 0
        filtro_dia_inicio = None
        
        if is_complex:
            # Lógica para slots que viram a semana (ex: MON 2200 TIL TUE 0200)
            h_ini_str, h_fim_str = c_hora_ini, c_hora_fim
            idx_ini = WEEK_MAP[c_dia_ini]
            idx_fim = WEEK_MAP[c_dia_fim]
            filtro_dia_inicio = idx_ini 
            if idx_fim >= idx_ini: offset_dias = idx_fim - idx_ini
            else: offset_dias = (7 - idx_ini) + idx_fim
        else:
            # Lógica simples de horário
            h_ini_str, h_fim_str = s_hora_ini, s_hora_fim
            # Se hora fim < hora início, assume +1 dia (exceto na burla do 1º dia)
            if int(h_fim_str) < int(h_ini_str): offset_dias = 1

        # Análise do texto ANTES do horário (Segmento)
        segmento = text[last_end:match.start()]
        last_end = match.end()
        
        datas_deste_segmento = []
        filtro_semana_deste_segmento = set()
        achou_nova_definicao = False

        tokens = re.findall(r'[A-Za-z0-9/]+', segmento)
        
        # Detecta se há intenção de data ou semana neste segmento
        tem_conteudo_data = any(t in MONTH_MAP or t[0].isdigit() for t in tokens)
        tem_conteudo_semana = any(t.split("/")[0] in WEEK_MAP for t in tokens)

        if tem_conteudo_data or tem_conteudo_semana:
            achou_nova_definicao = True
            k = 0 
            while k < len(tokens):
                tok = tokens[k]
                
                # Tratamento de barras (ex: MON/WED/FRI)
                if "/" in tok and not tok[0].isdigit():
                    partes = tok.split("/")
                    for p in partes:
                        if p in WEEK_MAP: filtro_semana_deste_segmento.add(WEEK_MAP[p])
                    k += 1; continue
                
                # Tratamento de Dias da Semana (MON, TUE...)
                if tok in WEEK_MAP:
                    idx_tok = WEEK_MAP[tok]
                    # Verifica intervalo (MON TIL FRI)
                    if k + 2 < len(tokens) and tokens[k+1] == "TIL":
                        alvo_tok = tokens[k+2]
                        if alvo_tok in WEEK_MAP:
                            idx_alvo = WEEK_MAP[alvo_tok]
                            if idx_tok <= idx_alvo: 
                                filtro_semana_deste_segmento.update(range(idx_tok, idx_alvo + 1))
                            else: 
                                filtro_semana_deste_segmento.update(range(idx_tok, 7))
                                filtro_semana_deste_segmento.update(range(0, idx_alvo + 1))
                            k += 3; continue
                    
                    filtro_semana_deste_segmento.add(idx_tok); k += 1
                else: 
                    k += 1
            
            # Tratamento de Datas (JAN 10, 10/11/12)
            i = 0 
            while i < len(tokens):
                tok = tokens[i]
                # Pula tokens já processados ou irrelevantes
                if tok in WEEK_MAP or ("/" in tok and not tok[0].isdigit()): i += 1; continue
                if tok == "TIL" and i>0 and (tokens[i-1] in WEEK_MAP or ("/" in tokens[i-1] and not tokens[i-1][0].isdigit())): i += 1; continue
                
                if tok in MONTH_MAP: 
                    contexto_mes = MONTH_MAP[tok]; i += 1; continue
                
                if tok[0].isdigit():
                    # Intervalo de Datas (10 TIL 15)
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
                    
                    # Lista de Datas (10/11/12)
                    if "/" in tok: 
                        for p in tok.split("/"):
                            dt = criar_data_segura(contexto_ano, contexto_mes, int(p))
                            if dt: datas_deste_segmento.append(dt)
                        i += 1; continue
                    else:
                        # Data única (10)
                        dt = criar_data_segura(contexto_ano, contexto_mes, int(tok))
                        if dt: datas_deste_segmento.append(dt)
                        i += 1; continue
                i += 1
            
            # --- V18.6 FIX: FALLBACK DE DATAS ---
            # Se achamos filtro de semana (ex: TUE TIL SAT) mas nenhuma data específica,
            # geramos todas as datas entre B e C para aplicar o filtro depois.
            if not datas_deste_segmento and filtro_semana_deste_segmento:
                curr = dt_b
                # Loop seguro até C
                while curr <= dt_c + timedelta(days=1): 
                    if curr > dt_c: break
                    datas_deste_segmento.append(curr)
                    curr += timedelta(days=1)

            # Se não achou nada novo, herda do anterior
            if not datas_deste_segmento and not filtro_semana_deste_segmento and ultima_lista_datas: 
                datas_deste_segmento = list(ultima_lista_datas)

        elif "DLY" in segmento or "DAILY" in segmento:
            # Rotina Diária: Gera todos os dias entre B e C
            curr = dt_b
            while curr <= dt_c: datas_deste_segmento.append(curr); curr += timedelta(days=1)
            achou_nova_definicao = True

        # Atualiza memória de contexto
        if achou_nova_definicao:
            ultima_lista_datas = datas_deste_segmento
            ultimo_filtro_semana = filtro_semana_deste_segmento
        else:
            datas_deste_segmento = ultima_lista_datas
            filtro_semana_deste_segmento = ultimo_filtro_semana

        # 5. Geração e Validação dos Slots
        for dt_crua in datas_deste_segmento:
            dt_final = ajustar_ano_referencia(dt_crua, dt_b)
            if not dt_final: continue
            
            # Aplica filtro de semana, se houver
            if is_complex and filtro_dia_inicio is not None:
                # Regra Complexa: o dia de início tem que bater com o dia explícito (MON...)
                if dt_final.weekday() != filtro_dia_inicio: continue
            elif filtro_semana_deste_segmento and dt_final.weekday() not in filtro_semana_deste_segmento:
                continue
            
            # Monta o Slot
            s_ini_teorico = dt_final.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
            s_ini = max(s_ini_teorico, dt_b) # Clipping B
            
            s_fim = dt_final.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
            
            # --- BURLA DE 1 MINUTO (V18.5) ---
            # Se Início >= Fim no mesmo dia e NÃO é rotina diária/pernoite explícito
            if s_ini >= s_fim and not ("DLY" in segmento or "DAILY" in segmento):
                s_fim = s_ini + timedelta(minutes=1)
            else:
                # Rotina normal ou Pernoite
                s_fim += timedelta(days=offset_dias)
            
            # Clipping C e Validação Final
            if s_fim <= dt_b or s_ini >= dt_c: continue
            
            slots.append({'inicio': s_ini, 'fim': min(s_fim, dt_c)})

    # Ordena cronologicamente
    slots.sort(key=lambda x: x['inicio'])
    return slots

# ==============================================================================
# BLOCO DE TESTE RÁPIDO
# ==============================================================================
if __name__ == "__main__":
    # Teste do Caso 74 (Zero Slots)
    print("--- Teste Unitário V18.6 ---")
    b = "2602100420"
    c = "2603070720"
    d = "TUE TIL SAT 0420-0720"
    
    resultado = interpretar_periodo_atividade(d, "TESTE", b, c)
    print(f"Entrada: {d}")
    print(f"Slots Gerados: {len(resultado)}")
    if len(resultado) > 0:
        print(f"Primeiro: {resultado[0]}")
        print(f"Último: {resultado[-1]}")
    else:
        print("ALERTA: Zero slots gerados!")