import re
from datetime import datetime, timedelta

# Mapa de meses para converter texto em número
MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    "FEV": 2, "ABR": 4, "MAI": 5, "AGO": 8, "SET": 9, "OUT": 10, "DEZ": 12
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

def ajustar_ano_data(dia, mes, dt_referencia):
    """
    Cria uma data usando o ano da referência.
    Se o mês da data for menor que o mês da referência (virada de ano), soma 1 ano.
    """
    ano = dt_referencia.year
    try:
        dt_criada = datetime(ano, mes, dia)
        # Se a data criada ficou muito no passado (ex: Jan 2026 quando estamos em Dez 2025), ajusta
        # Lógica simples: se o mês alvo é menor que o mês ref e estamos no fim do ano...
        # Mas para NOTAMs, geralmente a data B é o melhor guia.
        if dt_criada.month < dt_referencia.month and dt_referencia.month > 10:
             dt_criada = dt_criada.replace(year=ano + 1)
        return dt_criada
    except:
        return None

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    V2: Suporte a DLY (Caso 1) e Listas de Dias Soltos (Caso 2).
    Estratégia: Segmentação por Horário.
    """
    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    
    if not dt_b or not dt_c: return []

    slots = []
    text = item_d_text.upper().strip()
    
    # Regex para capturar horários (HHMM-HHMM)
    # Usamos finditer para pegar todos os horários e suas posições
    re_horario = re.compile(r'(\d{4})-(\d{4})')
    matches = list(re_horario.finditer(text))
    
    last_end = 0
    contexto_mes = dt_b.month # Começa assumindo o mês da data de início

    # Se não achou nenhum horário explícito no texto, mas tem datas B/C válidas,
    # Pode ser um caso de DLY implícito ou texto mal formatado. 
    # Por enquanto, retornamos vazio ou B-C se não houver matches, 
    # mas o foco aqui são os casos com horário.
    if not matches:
        # Fallback de segurança (comporta-se como DLY para o período todo se não tiver horário no texto)
        return [{'inicio': dt_b, 'fim': dt_c}]

    for match in matches:
        h_ini_str, h_fim_str = match.groups()
        
        # Pega o texto ANTES deste horário (desde o último horário processado)
        # Ex: "JAN 20 23 27 30 " antes de "1100-1900"
        segmento = text[last_end:match.start()].strip()
        last_end = match.end()
        
        # --- LÓGICA DE DECISÃO ---
        
        # 1. Checa se é DLY (Regra do Caso 1)
        if "DLY" in segmento:
            # Gera slots para todos os dias entre B e C
            curr = dt_b
            while curr <= dt_c:
                s_ini = curr.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
                s_fim = curr.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
                if s_fim < s_ini: s_fim += timedelta(days=1)
                
                # Otimização: Só adiciona se estiver dentro da validade global (com margem)
                if s_fim >= dt_b and s_ini <= dt_c:
                    slots.append({'inicio': s_ini, 'fim': s_fim})
                curr += timedelta(days=1)
                
        # 2. Checa se tem DIAS ESPECÍFICOS (Regra do Caso 2)
        # Procura por meses (JAN, FEB...) e números (20, 23...)
        else:
            # Tenta atualizar o contexto de mês
            for nome_mes, num_mes in MONTH_MAP.items():
                if nome_mes in segmento:
                    contexto_mes = num_mes
                    break
            
            # Encontra todos os números soltos no segmento (dias)
            # Regex \b\d{1,2}\b pega números de 1 ou 2 dígitos isolados
            dias_encontrados = re.findall(r'\b(\d{1,2})\b', segmento)
            
            if dias_encontrados:
                for dia_str in dias_encontrados:
                    try:
                        dia = int(dia_str)
                        # Cria a data baseada no ano de dt_b e mês do contexto
                        dt_base = ajustar_ano_data(dia, contexto_mes, dt_b)
                        
                        if dt_base:
                            s_ini = dt_base.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
                            s_fim = dt_base.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
                            if s_fim < s_ini: s_fim += timedelta(days=1)
                            
                            slots.append({'inicio': s_ini, 'fim': s_fim})
                    except:
                        pass # Ignora números inválidos (ex: dia 32)

    return slots