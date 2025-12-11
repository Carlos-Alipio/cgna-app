import re
from datetime import datetime, timedelta

# ==============================================================================
# LÓGICA V11.0 - DESAMBIGUAÇÃO (SEPARA DATA DE SEMANA)
# ==============================================================================
def interpretar_periodo_atividade(texto_bruto):
    if not isinstance(texto_bruto, str) or not texto_bruto:
        return []

    # 1. Normalização e Correção de Typos
    texto = texto_bruto.upper().strip()
    
    # Padronizações básicas
    texto = re.sub(r'([A-Z]{3})/([A-Z]{3})', r'\1', texto) # MON/TUE -> MON
    texto = re.sub(r'(\d{1,2})/(\d{1,2})', r'\1', texto)   # 01/02 -> 01
    
    # Correção de OCR/Typos comuns (0CT, 1AN...)
    replacements = {
        '0CT': 'OCT', '1AN': 'JAN', 'F3B': 'FEB', 
        'M0N': 'MON', 'TU3': 'TUE', 'W3D': 'WED'
    }
    for erro, corr in replacements.items():
        texto = texto.replace(erro, corr)

    # Mapas
    mapa_meses = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    mapa_semana = {
        'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6
    }

    # Regex separador de horários
    regex_hora = re.compile(r'(\d{4}[/-]\d{4})')
    matches = list(regex_hora.finditer(texto))
    
    if not matches:
        return ["ERRO: Nenhum horário identificado."]

    lista_deltas = []
    
    # Estado Global
    ano_atual = datetime.now().year
    curr_mes = datetime.now().month
    curr_ano = ano_atual
    
    # Memória de Contexto (Range de datas ativo)
    ctx_range_start = None
    ctx_range_end = None
    
    last_end = 0 
    
    for match in matches:
        horario_str = match.group(1)
        start_idx, end_idx = match.span()
        
        # Pega o texto do segmento atual
        segmento_texto = texto[last_end:start_idx].strip()
        last_end = end_idx

        # ======================================================================
        # PASSO A: EXTRAÇÃO DE FILTROS DE SEMANA (ANTES DE TUDO)
        # ======================================================================
        # Removemos os dias da semana do texto para que o 'TIL' deles não confunda
        # a leitura das datas.
        
        weekdays_slot = set()
        
        # A.1. Intervalos de Semana (MON TIL FRI)
        # Regex procura padrões de semana e os consome
        regex_wk_range = r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+TIL\s+(MON|TUE|WED|THU|FRI|SAT|SUN)'
        
        # Loop para achar todos os intervalos de semana no segmento
        for m_wk in re.finditer(regex_wk_range, segmento_texto):
            d_start = mapa_semana[m_wk.group(1)]
            d_end = mapa_semana[m_wk.group(2)]
            
            # Adiciona ao set
            curr = d_start
            while True:
                weekdays_slot.add(curr)
                if curr == d_end: break
                curr = (curr + 1) % 7
            
            # Remove do texto, substituindo por espaço para não colar palavras
            segmento_texto = segmento_texto.replace(m_wk.group(0), ' ')

        # A.2. Dias Soltos (MON WED)
        # Varre o que sobrou do texto procurando dias soltos
        for dia_nome, dia_idx in mapa_semana.items():
            if dia_nome in segmento_texto:
                weekdays_slot.add(dia_idx)
                # Remove do texto
                segmento_texto = segmento_texto.replace(dia_nome, ' ')

        tem_filtro_semana = len(weekdays_slot) > 0

        # ======================================================================
        # PASSO B: TOKENIZER DE DATAS (O QUE SOBROU DO TEXTO)
        # ======================================================================
        # Agora o 'segmento_texto' está limpo de dias da semana.
        # Qualquer 'TIL' que sobrou aqui é de DATA.
        
        tokens = segmento_texto.split()
        dias_coletados = []
        
        # Se não sobrou nada (vazio ou só espaços), usamos o contexto anterior
        if not tokens and ctx_range_start:
             # Recupera o range da memória
             c = ctx_range_start
             while c <= ctx_range_end:
                 dias_coletados.append(c)
                 c += timedelta(days=1)
        
        else:
            # Processa tokens de data
            i = 0
            while i < len(tokens):
                token = tokens[i]
                
                # B.1. Mês
                if token in mapa_meses:
                    nm = mapa_meses[token]
                    if curr_mes == 12 and nm == 1: curr_ano += 1
                    curr_mes = nm
                
                # B.2. Range de Datas (TIL)
                elif token == 'TIL':
                    # Pega o último dia adicionado como start
                    if dias_coletados and (i + 1 < len(tokens)):
                        start_date = dias_coletados.pop() # Recupera o dia imediatamente anterior
                        
                        # Analisa o próximo token (Fim do Range)
                        prox = tokens[i+1]
                        i += 1
                        
                        end_m = curr_mes
                        end_y = curr_ano
                        
                        # Se for Mês (TIL DEC 10)
                        if prox in mapa_meses:
                            end_m = mapa_meses[prox]
                            if curr_mes == 12 and end_m == 1: end_y += 1
                            # Precisa do dia depois do mês
                            if i + 1 < len(tokens): 
                                prox = tokens[i+1]
                                i += 1
                        
                        # Se for Número (Dia)
                        if prox.isdigit():
                            try:
                                end_date = datetime(end_y, end_m, int(prox))
                                
                                # Atualiza Memória Global
                                ctx_range_start = start_date
                                ctx_range_end = end_date
                                curr_mes = end_m
                                curr_ano = end_y
                                
                                # Gera os dias
                                c = start_date
                                while c <= end_date:
                                    dias_coletados.append(c)
                                    c += timedelta(days=1)
                            except: pass

                # B.3. Número (Dia Pontual)
                elif token.isdigit():
                    try:
                        dt = datetime(curr_ano, curr_mes, int(token))
                        dias_coletados.append(dt)
                    except: pass
                
                i += 1

        # ======================================================================
        # PASSO C: FILTRAGEM E GERAÇÃO
        # ======================================================================
        
        # Remove duplicatas e ordena
        dias_finais = sorted(list(set(dias_coletados)))
        
        sep = '-' if '-' in horario_str else '/'
        h_split = horario_str.split(sep)
        h_ini, m_ini = int(h_split[0][:2]), int(h_split[0][2:])
        h_fim, m_fim = int(h_split[1][:2]), int(h_split[1][2:])
        cruza_meia_noite = (h_fim < h_ini) or (h_fim == h_ini and m_fim < m_ini)

        for dt in dias_finais:
            # Aplica filtro de semana
            if tem_filtro_semana and dt.weekday() not in weekdays_slot:
                continue

            dt_i = dt.replace(hour=h_ini, minute=m_ini)
            if cruza_meia_noite:
                dt_f = (dt + timedelta(days=1)).replace(hour=h_fim, minute=m_fim)
            else:
                dt_f = dt.replace(hour=h_fim, minute=m_fim)
            
            lista_deltas.append(f"{dt_i.strftime('%d/%m/%Y %H:%M')}|{dt_f.strftime('%d/%m/%Y %H:%M')}")

    return "\n".join(lista_deltas)

# ==============================================================================
# TESTER
# ==============================================================================
if __name__ == "__main__":
    caso_critico = "SEP 22 TIL OCT 24 MON TIL FRI 0450-0720 0CT 26 TIL DEC 13 MON 0450-0740 TUE TIL SUN 0301-0800"
    
    print("🛠️ TESTER V11 - LOGIC FIX (TIL AMBIGUITY)")
    print(f"\nEntrada:\n{caso_critico}\n")
    print("Saída:")
    print(interpretar_periodo_atividade(caso_critico))
    
    print("\n⌨️ --- MODO INTERATIVO ---")
    while True:
        txt = input("\n✍️ Cole o Item D: ")
        if txt.lower() == 'sair': break
        print(f"\n{interpretar_periodo_atividade(txt)}")