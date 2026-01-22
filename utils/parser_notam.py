import re
from datetime import datetime, timedelta

def parse_notam_date(date_str):
    """
    Converte string crua do NOTAM (YYMMDDHHMM) em datetime.
    """
    try:
        if not date_str: return None
        clean_str = str(date_str).replace("-", "").replace(":", "").replace(" ", "").strip()
        # Tratamento básico para 10 ou 12 dígitos
        if len(clean_str) == 10:
            return datetime.strptime(clean_str, "%y%m%d%H%M")
        elif len(clean_str) == 12:
            return datetime.strptime(clean_str, "%Y%m%d%H%M")
        return None
    except:
        return None

def interpretar_periodo_atividade(item_d_text, icao, item_b_raw, item_c_raw):
    """
    V1: Implementação Mínima para DLY (Diário).
    Foco: Resolver 'DLY 0320-0750'.
    """
    # 1. Parse das datas Limites (B e C)
    dt_b = parse_notam_date(item_b_raw)
    dt_c = parse_notam_date(item_c_raw)
    
    if not dt_b or not dt_c:
        return []

    slots = []
    text = item_d_text.upper().strip()

    # 2. Lógica Específica: DLY + Horário (HHMM-HHMM)
    # Regex simples: Procura por 4 dígitos - 4 dígitos
    match_horario = re.search(r'(\d{4})-(\d{4})', text)
    
    if "DLY" in text and match_horario:
        h_ini_str = match_horario.group(1)
        h_fim_str = match_horario.group(2)
        
        # Cria um slot para cada dia no intervalo
        curr = dt_b
        while curr <= dt_c:
            # Constrói o horário de início e fim para o dia 'curr'
            # Substitui a hora do dia atual pela hora encontrada no texto
            slot_ini = curr.replace(hour=int(h_ini_str[:2]), minute=int(h_ini_str[2:]))
            slot_fim = curr.replace(hour=int(h_fim_str[:2]), minute=int(h_fim_str[2:]))
            
            # Tratamento de virada de noite (ex: 2300-0200)
            if slot_fim < slot_ini:
                slot_fim += timedelta(days=1)
            
            # Validação: O slot gerado deve estar dentro da vigência do NOTAM (aprox)
            # Adicionamos o slot à lista
            slots.append({'inicio': slot_ini, 'fim': slot_fim})
            
            curr += timedelta(days=1)
            
    # Fallback: Se não encontrou lógica DLY, retorna o período total (Segurança)
    if not slots:
        slots.append({'inicio': dt_b, 'fim': dt_c})

    return slots