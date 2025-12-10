from datetime import datetime
import pandas as pd
from utils.notam_codes import NOTAM_SUBJECT, NOTAM_CONDITION

def formatar_data_notam(valor):
    """
    Função Universal:
    - Aceita formato Aviação (2512092145)
    - Aceita formato Banco ISO (2025-12-09 21:45:00)
    - Aceita objeto Timestamp do Pandas
    Retorna sempre: dd/mm/YYYY HH:mm
    """
    if valor is None: return "-"
    
    # Converte para string e limpa espaços
    texto = str(valor).strip()
    
    # Se for vazio, retorna traço
    if not texto or texto.lower() == 'nan' or texto.lower() == 'nat':
        return "-"

    try:
        # TENTATIVA 1: Formato do Banco de Dados (ISO)
        # Se tiver traço e dois pontos (Ex: 2025-12-09 21:45:00)
        if "-" in texto and ":" in texto:
            # O Pandas é muito bom em adivinhar formatos de banco
            data_obj = pd.to_datetime(texto)
            return data_obj.strftime("%d/%m/%Y %H:%M")

        # TENTATIVA 2: Formato Aviação (10 dígitos numéricos: YYMMDDHHmm)
        if len(texto) == 10 and texto.isdigit():
            data_obj = datetime.strptime(texto, "%y%m%d%H%M")
            return data_obj.strftime("%d/%m/%Y %H:%M")
            
    except Exception:
        pass # Se der erro em qualquer conversão, cai aqui embaixo

    # Se não for data (ex: "PERM", "EST"), devolve o texto original
    return texto

def decodificar_q_code(valor_bruto):
    q_string = str(valor_bruto).strip().upper()
    if len(q_string) < 4 or q_string in ["NONE", "NAN"]:
        return "Outros", "Ver Texto", "XX", "XX"
    try:
        code = q_string[1:5] if q_string.startswith("Q") and len(q_string) >= 5 else q_string[:4]
        ass_cod, cond_cod = code[:2], code[2:4]
        return NOTAM_SUBJECT.get(ass_cod, ass_cod), NOTAM_CONDITION.get(cond_cod, cond_cod), ass_cod, cond_cod
    except:
        return "Erro", "Erro", "XX", "XX"