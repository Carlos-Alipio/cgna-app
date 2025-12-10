from datetime import datetime
# Se você moveu o notam_codes.py para a pasta utils, use: from .notam_codes import ...
# Se ele continua na raiz, use: from notam_codes import ...
from notam_codes import NOTAM_SUBJECT, NOTAM_CONDITION 

def formatar_data_notam(texto_bruto):
    if not isinstance(texto_bruto, str): return "-"
    texto = texto_bruto.strip()
    if not texto.isdigit() or len(texto) != 10: return texto 
    try:
        return datetime.strptime(texto, "%y%m%d%H%M").strftime("%d/%m/%Y %H:%M")
    except: return texto

def decodificar_q_code(valor_bruto):
    q_string = str(valor_bruto).strip().upper()
    if len(q_string) < 4 or q_string in ["NONE", "NAN"]:
        return "Outros", "Ver Texto", "XX", "XX"
    try:
        code = q_string[1:5] if q_string.startswith("Q") and len(q_string) >= 5 else q_string[:4]
        ass_cod, cond_cod = code[:2], code[2:4]
        # Pega do dicionário importado
        return NOTAM_SUBJECT.get(ass_cod, ass_cod), NOTAM_CONDITION.get(cond_cod, cond_cod), ass_cod, cond_cod
    except:
        return "Erro", "Erro", "XX", "XX"