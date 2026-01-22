# Lista de Casos que JÁ FUNCIONAM e não podem quebrar
# Estrutura: Input (B, C, D) + Output Esperado (Snapshot)

CASOS_BLINDADOS = [
    {
        "id": "CASO_01",
        "desc": "DLY Simples (26/01 a 13/02)",
        "b": "2601260320",
        "c": "2602130750",
        "d": "DLY 0320-0750",
        "esperado": {
            "qtd_slots": 19,
            "primeiro_inicio": "26/01/2026 03:20",
            "ultimo_fim": "13/02/2026 07:50"
        }
    },
    {
        "id": "CASO_02",
        "desc": "Listas de Dias Soltos (JAN 20, 23...)",
        "b": "2601201100",
        "c": "2601301900",
        "d": "JAN 20 23 27 30 1100-1900 JAN 22 1600-2200 JAN 24 1100-1600 JAN 29 1600-2100",
        "esperado": {
            "qtd_slots": 7,
            "primeiro_inicio": "20/01/2026 11:00",
            "ultimo_fim": "30/01/2026 19:00"
        }
    },
    {
        "id": "CASO_03",
        "desc": "Scanner Linear com Herança de Mês (FEB/MAR) e Tokenizer",
        "b": "2602010440",
        "c": "2603260745",
        "d": "FEB 01 03 TIL 11 MAR 09 TIL 13 0440-0745 23 TIL 26 0450-0745",
        "esperado": {
            "qtd_slots": 19,
            "primeiro_inicio": "01/02/2026 04:40",
            "ultimo_fim": "26/03/2026 07:45"
        }
    },
    {
        "id": "CASO_04",
        "desc": "Múltiplos Meses e Retorno Temporal (Jan -> Mar -> Jan)",
        "b": "2601070830",
        "c": "2603251130",
        "d": "JAN 07 14 21 FEB 04 11 18 25 MAR 04 11 18 25 0830-1130 JAN 27 TIL 31 0800-1300",
        "esperado": {
            "qtd_slots": 16,
            "primeiro_inicio": "07/01/2026 08:30",
            "ultimo_fim": "25/03/2026 11:30"
        }
    },
    {
        "id": "CASO_05",
        "desc": "Complexo: Múltiplos Ranges e Flashback de Mês",
        "b": "2512190301",
        "c": "2601280900",
        "d": "DEC 19 TIL 20 29 TIL 31 JAN 01 TIL 03 13 TIL 17 27 TIL 28 0301-0900 DEC 22 TIL 26 JAN 05 TIL 09 19 TIL 23 1700-2100",
        "esperado": {
            "qtd_slots": 30,
            "primeiro_inicio": "19/12/2025 03:01",
            "ultimo_fim": "28/01/2026 09:00"
        }
    },
    {
        "id": "CASO_06",
        "desc": "Range Multi-Mês (FEB-APR) com Filtro de Dia da Semana",
        "b": "2601100400",
        "c": "2604100759",
        "d": "JAN 10 TIL 16 TUE WED THU FRI SAT 0400-0759 JAN 17 TIL 30 TUE WED THU FRI SAT 0440-0830 FEB 02 TIL APR 10 MON TUE 0500-0759",
        "esperado": {
            "qtd_slots": 35,
            "primeiro_inicio": "10/01/2026 04:00",
            "ultimo_fim": "07/04/2026 07:59"
        }
    },
    {
        "id": "CASO_07",
        "desc": "Múltiplos Horários com Herança de Mês Implícita (JAN)",
        "b": "2512191300",
        "c": "2601282000",
        "d": "DEC 19 29 TIL 31 1300-2000 DEC 22 TIL 27 0301-0900 JAN 01 02 12 TIL 16 26 TIL 28 1300-2000 06 TIL 10 20 TIL 24 0301-0900",
        "esperado": {
            "qtd_slots": 30,
            "primeiro_inicio": "19/12/2025 13:00",
            "ultimo_fim": "28/01/2026 20:00"
        }
    },
    {
        "id": "CASO_08",
        "desc": "Range de Dias da Semana (TUE TIL SAT)",
        "b": "2601120340",
        "c": "2602140750",
        "d": "JAN 12 TIL 15 17 TIL 22 24 TIL 30 0340-0750 FEV 03 TIL 14 TUE TIL SAT 0340-0750",
        "esperado": {
            "qtd_slots": 27,
            "primeiro_inicio": "12/01/2026 03:40",
            "ultimo_fim": "14/02/2026 07:50"
        }
    },
    {
        "id": "CASO_09",
        "desc": "Redundância de Mês no Range (JAN... TIL JAN...)",
        "b": "2601110330",
        "c": "2604090759",
        "d": "JAN 11 TIL JAN 26 MON SUN 0330-0759 JAN 28 TIL APR 9 WED THU 0330-0759",
        "esperado": {
            "qtd_slots": 28,
            "primeiro_inicio": "11/01/2026 03:30",
            "ultimo_fim": "09/04/2026 07:59"
        }
    },
    {
        "id": "CASO_10",
        "desc": "Múltiplos Horários na mesma lista (Herança)",
        "b": "2601170340",
        "c": "2602150820",
        "d": "JAN 17 18 20 22 24 25 27 29 31 FEB 01 TIL 15 0340-0820 JAN 19 21 23 26 28 30 0340-0820 0915-1200",
        "esperado": {
            "qtd_slots": 36,
            "primeiro_inicio": "17/01/2026 03:40",
            "ultimo_fim": "15/02/2026 08:20"
        }
    },
    {
        "id": "CASO_11",
        "desc": "Listas de Datas Distintas com Horários Diferentes",
        "b": "2601051000",
        "c": "2601301550",
        "d": "JAN 05 08 10 12 15 17 19 22 24 26 29 1000-1620 JAN 06 07 09 13 14 16 20 21 23 27 28 30 1000-1550",
        "esperado": {
            "qtd_slots": 23,
            "primeiro_inicio": "05/01/2026 10:00",
            "ultimo_fim": "30/01/2026 15:50"
        }
    },
    {
        "id": "CASO_12",
        "desc": "Troca de Horário com Continuação de Mês (Jan 17 18... 19 21)",
        "b": "2601170450",
        "c": "2603280755",
        "d": "JAN 17 18 0450-0735 19 21 24 31 FEB 07 08 09 11 14 MAR 07 08 09 11 14 21 28 0455-0755",
        "esperado": {
            "qtd_slots": 18,
            "primeiro_inicio": "17/01/2026 04:50",
            "ultimo_fim": "28/03/2026 07:55"
        }
    },
    {
        "id": "CASO_13",
        "desc": "DLY com Filtro de Bordas (Corte de horário fora da vigência)",
        "b": "2512232030",
        "c": "2603182100",
        "d": "DLY 1000-1030 2030-2100",
        "esperado": {
            "qtd_slots": 171, # 172 brutos - 1 (do dia 23/12 às 10:00)
            "primeiro_inicio": "23/12/2025 20:30",
            "ultimo_fim": "18/03/2026 21:00"
        }
    },
    {
        "id": "CASO_14",
        "desc": "DLY com Limites Exatos (Início e Fim coincidem com Horário)",
        "b": "2602031200",
        "c": "2602062000",
        "d": "DLY 1200-2000",
        "esperado": {
            "qtd_slots": 4,
            "primeiro_inicio": "03/02/2026 12:00",
            "ultimo_fim": "06/02/2026 20:00"
        }
    },
    {
        "id": "CASO_15",
        "desc": "DLY Limites Exatos II (Reconfirmação)",
        "b": "2602091200",
        "c": "2602122000",
        "d": "DLY 1200-2000",
        "esperado": {
            "qtd_slots": 4,
            "primeiro_inicio": "09/02/2026 12:00",
            "ultimo_fim": "12/02/2026 20:00"
        }
    },
    {
        "id": "CASO_16",
        "desc": "Sintaxe com Barra (DEC 01/02 e MON/TUE) + Herança de Dias",
        "b": "2512012133",
        "c": "2602281630",
        "d": "DEC 01/02 2133-0115 DEC 02 TIL FEB 28 MON TUE THU 0745-1630 WED FRI 1020-1600 SAT 0745-1630 DEC 02 TIL JAN 30 MON/TUE TIL THU/FRI 1940-0115 FRI/SAT 2040-0115",
        "esperado": {
            "qtd_slots": 130,
            "primeiro_inicio": "01/12/2025 21:33",
            "ultimo_fim": "28/02/2026 16:30"  # <--- CORRIGIDO AQUI (Era 07:45)
        }
    },
    {
        "id": "CASO_17",
        "desc": "Item D Vazio ou Genérico (Evento Único B -> C)",
        "b": "2602080825",
        "c": "2602081155",
        "d": "", # Campo vazio
        "esperado": {
            "qtd_slots": 1,
            "primeiro_inicio": "08/02/2026 08:25",
            "ultimo_fim": "08/02/2026 11:55"
        }
    },
    {
        "id": "CASO_18",
        "desc": "Item D Vazio (Longa Duração / Virada de Ano)",
        "b": "2512301809",
        "c": "2603300900",
        "d": "",
        "esperado": {
            "qtd_slots": 1,
            "primeiro_inicio": "30/12/2025 18:09",
            "ultimo_fim": "30/03/2026 09:00"
        }
    },
    {
        "id": "CASO_19",
        "desc": "PERM no campo C (Fim = Início + 365 dias)",
        "b": "2512122117",
        "c": "PERM",
        "d": "",
        "esperado": {
            "qtd_slots": 1,
            "primeiro_inicio": "12/12/2025 21:17",
            "ultimo_fim": "12/12/2026 21:17"
        }
    },
    {
        "id": "CASO_20",
        "desc": "Misto: Data Única + Range DLY com múltiplos horários (Precedência)",
        "b": "2601051800",
        "c": "2603152130",
        "d": "JAN 05 1800-2130 JAN 06 TIL MAR 15 DLY 0800-1230 1800-2130",
        "esperado": {
            "qtd_slots": 139,
            "primeiro_inicio": "05/01/2026 18:00",
            "ultimo_fim": "15/03/2026 21:30"
        }
    },
    {
        "id": "CASO_21",
        "desc": "Mix de Lista de Dias e Dias Únicos (Teste de Estabilidade)",
        "b": "2601201100",
        "c": "2601301900",
        "d": "JAN 20 23 27 30 1100-1900 JAN 22 1600-2200 JAN 24 1100-1600 JAN 29 1600-2100",
        "esperado": {
            "qtd_slots": 7,
            "primeiro_inicio": "20/01/2026 11:00",
            "ultimo_fim": "30/01/2026 19:00"
        }
    },
    {
        "id": "CASO_22",
        "desc": "Data Específica + Range Longo (Sem keyword DLY)",
        "b": "2511091834",
        "c": "2602062100",
        "d": "NOV 09 1834-2100 NOV 10 TIL FEB 06 0900-2100",
        "esperado": {
            "qtd_slots": 90,
            "primeiro_inicio": "09/11/2025 18:34",
            "ultimo_fim": "06/02/2026 21:00"
        }
    },
    {
        "id": "CASO_23",
        "desc": "Lista Disjunta (JAN/FEB/MAR) + Range Específico (JAN 27-31)",
        "b": "2601070830",
        "c": "2603251130",
        "d": "JAN 07 14 21 FEB 04 11 18 25 MAR 04 11 18 25 0830-1130 JAN 27 TIL 31 0800-1300",
        "esperado": {
            "qtd_slots": 16,
            "primeiro_inicio": "07/01/2026 08:30",
            "ultimo_fim": "25/03/2026 11:30"
        }
    },
    {
        "id": "CASO_24",
        "desc": "Limite C (00:00) cortando o último dia do Texto (TIL APR 30)",
        "b": "2602031200",
        "c": "2604300000",
        "d": "FEB 03 TIL APR 30 DLY 1200-0000",
        "esperado": {
            "qtd_slots": 86,
            "primeiro_inicio": "03/02/2026 12:00",
            "ultimo_fim": "30/04/2026 00:00" # Fim do slot do dia 29
        }
    },
    {
        "id": "CASO_25",
        "desc": "Complexo: Múltiplos Ranges de Datas + Filtro de Dias da Semana",
        "b": "2601120340",
        "c": "2602140750",
        "d": "JAN 12 TIL 15 17 TIL 22 24 TIL 30 0340-0750 FEV 03 TIL 14 TUE TIL SAT 0340-0750",
        "esperado": {
            "qtd_slots": 27,
            "primeiro_inicio": "12/01/2026 03:40",
            "ultimo_fim": "14/02/2026 07:50"
        }
    },
    {
        "id": "CASO_26",
        "desc": "Múltiplos Grupos de Datas Específicas com Horários Diferentes",
        "b": "2601170450",
        "c": "2603280755",
        "d": "JAN 17 18 0450-0735 19 21 24 31 FEB 07 08 09 11 14 MAR 07 08 09 11 14 21 28 0455-0755",
        "esperado": {
            "qtd_slots": 18,
            "primeiro_inicio": "17/01/2026 04:50",
            "ultimo_fim": "28/03/2026 07:55"
        }
    },
    {
        "id": "CASO_27",
        "desc": "Cronologia Alternada (JAN/FEB depois volta JAN) + Herança de Horário Duplo",
        "b": "2601170340",
        "c": "2602150820",
        "d": "JAN 17 18 20 22 24 25 27 29 31 FEB 01 TIL 15 0340-0820 JAN 19 21 23 26 28 30 0340-0820 0915-1200",
        "esperado": {
            "qtd_slots": 36,
            "primeiro_inicio": "17/01/2026 03:40",
            "ultimo_fim": "15/02/2026 08:20" 
            # Nota: O último cronológico é 15/02, 
            # embora JAN 30 tenha horários posteriores no texto, 
            # a data mais tardia é FEB 15.
        }
    },
    {
        "id": "CASO_28",
        "desc": "O Chefão: Híbrido Data+Hora, Semanas Cruzadas e Dias com Barra (WED/THU)",
        "b": "2601181543",
        "c": "2604122359",
        "d": "JAN 18 1543 TIL 20 2129 JAN 21 TIL JAN 31 SUN 0931 TIL TUE 2129 WED/THU FRI/SAT 0931-2129 FEB 01/02 0931-2359 FEB 03 0000-2029 FEB 04 TIL APR 11 SUN 0831 TIL TUE 2029 WED/THU FRI/SAT 0831-2029 APR 12 0831-2359",
        "esperado": {
            "qtd_slots": 63,
            "primeiro_inicio": "18/01/2026 15:43",
            "ultimo_fim": "12/04/2026 23:59"
        }
    },
    {
        "id": "CASO_29",
        "desc": "Básico: Lista de Dias Consecutivos (Sem TIL)",
        "b": "2601271245",
        "c": "2601281400",
        "d": "JAN 27 28 1245-1400",
        "esperado": {
            "qtd_slots": 2,
            "primeiro_inicio": "27/01/2026 12:45",
            "ultimo_fim": "28/01/2026 14:00"
        }
    },
    {
        "id": "CASO_30",
        "desc": "Listas de Datas Disjuntas com Horários Diferentes",
        "b": "2602021100",
        "c": "2603281100",
        "d": "FEB 02 11 20 MAR 01 09 18 1100-1200 MAR 28 1000-1100",
        "esperado": {
            "qtd_slots": 7,
            "primeiro_inicio": "02/02/2026 11:00",
            "ultimo_fim": "28/03/2026 11:00"
        }
    },
    {
        "id": "CASO_31",
        "desc": "Datas Disjuntas com Minutos Quebrados e Limite C Exato",
        "b": "2602021201",
        "c": "2603282059",
        "d": "FEB 02 11 20 MAR 01 09 18 1201-2159 MAR 28 1101-2059",
        "esperado": {
            "qtd_slots": 7,
            "primeiro_inicio": "02/02/2026 12:01",
            "ultimo_fim": "28/03/2026 20:59"
        }
    },
    {
        "id": "CASO_32",
        "desc": "Fronteiras Exatas: 1º Slot começa em B e Último Slot termina em C",
        "b": "2602022200",
        "c": "2603282200",
        "d": "FEB 02 11 20 MAR 01 09 18 2200-2300 MAR 28 2100-2200",
        "esperado": {
            "qtd_slots": 7,
            "primeiro_inicio": "02/02/2026 22:00",
            "ultimo_fim": "28/03/2026 22:00"
        }
    },
    {
        "id": "CASO_33",
        "desc": "Complexo: Datas órfãs (27) herdando horário do próximo grupo",
        "b": "2511201300",
        "c": "2601251210",
        "d": "NOV 20 1300-1410 27 DEC 05 13 21 1100-1210 31 1000-1110 JAN 08 16 25 1100-1210",
        "esperado": {
            "qtd_slots": 9,
            "primeiro_inicio": "20/11/2025 13:00",
            "ultimo_fim": "25/01/2026 12:10"
        }
    },
    {
        "id": "CASO_34",
        "desc": "Precisão de Minutos: Variação complexa com limites exatos em B e C",
        "b": "2511201411",
        "c": "2601252159",
        "d": "NOV 20 1411-2359 27 DEC 05 13 21 1211-2159 31 1111-2059 JAN 08 16 25 1211-2159",
        "esperado": {
            "qtd_slots": 9,
            "primeiro_inicio": "20/11/2025 14:11",
            "ultimo_fim": "25/01/2026 21:59"
        }
    },
    {
        "id": "CASO_35",
        "desc": "Midnight Start: Início às 00:00 e herança de datas",
        "b": "2511210000",
        "c": "2601252310",
        "d": "NOV 21 0000-0110 27 DEC 05 13 21 2200-2310 31 2100-2210 JAN 08 16 25 2200-2310",
        "esperado": {
            "qtd_slots": 9,
            "primeiro_inicio": "21/11/2025 00:00",
            "ultimo_fim": "25/01/2026 23:10"
        }
    },
    {
        "id": "CASO_36",
        "desc": "Acumulação Multi-mensal (DEC/JAN/FEB) com Herança de Horário Final",
        "b": "2511220945",
        "c": "2602131000",
        "d": "NOV 22 0945-1100 DEC 24 JAN 01 10 18 27 FEB 04 13 0845-1000",
        "esperado": {
            "qtd_slots": 8,
            "primeiro_inicio": "22/11/2025 09:45",
            "ultimo_fim": "13/02/2026 10:00"
        }
    },
    {
        "id": "CASO_37",
        "desc": "Ordem Não Cronológica: Texto volta para JAN após citar FEB",
        "b": "2511221101",
        "c": "2602131900",
        "d": "NOV 22 1101-2000 DEC 24 JAN 10 27 FEB 13 1001-1900 JAN 01 18 FEB 04 1001-2359",
        "esperado": {
            "qtd_slots": 8,
            "primeiro_inicio": "22/11/2025 11:01",
            "ultimo_fim": "13/02/2026 19:00"
        }
    },
    {
        "id": "CASO_38",
        "desc": "Ordem Não Cronológica com Horários da Madrugada (0000-0100)",
        "b": "2511222001",
        "c": "2602132000",
        "d": "NOV 22 2001-2100 DEC 24 JAN 10 27 FEB 13 1901-2000 JAN 02 19 FEB 05 0000-0100",
        "esperado": {
            "qtd_slots": 8,
            "primeiro_inicio": "22/11/2025 20:01",
            "ultimo_fim": "13/02/2026 20:00" 
            # O dia 13/02 é cronologicamente posterior ao dia 05/02 do último grupo.
        }
    },
    {
        "id": "CASO_39",
        "desc": "Range Syntax: Intervalo com barras (DEC 19/20 TIL FEB 15/16)",
        "b": "2512190900",
        "c": "2602160259",
        "d": "DEC 19/20 TIL FEB 15/16 0900-0259",
        "esperado": {
            "qtd_slots": 59,
            "primeiro_inicio": "19/12/2025 09:00",
            "ultimo_fim": "16/02/2026 02:59"
        }
    },
    {
        "id": "CASO_40",
        "desc": "DLY com múltiplos horários (1000-1030 2030-2100) e Corte no Início (B)",
        "b": "2512232030",
        "c": "2603182100",
        "d": "DLY 1000-1030 2030-2100",
        "esperado": {
            "qtd_slots": 171,
            "primeiro_inicio": "23/12/2025 20:30", # O horário das 10:00 foi cortado
            "ultimo_fim": "18/03/2026 21:00"
        }
    },
    {
        "id": "CASO_41",
        "desc": "Múltiplos Ranges (DEC-JAN, FEB) com Múltiplos Horários Compartilhados",
        "b": "2512241100",
        "c": "2602231900",
        "d": "DEC 24 TIL JAN 31 FEB 11 TIL 23 1100-1300 1700-1900",
        "esperado": {
            "qtd_slots": 104,
            "primeiro_inicio": "24/12/2025 11:00",
            "ultimo_fim": "23/02/2026 19:00"
        }
    },
    {
        "id": "CASO_42",
        "desc": "DLY Simples com Limites Exatos (Começa em B e Termina em C)",
        "b": "2601260320",
        "c": "2602130750",
        "d": "DLY 0320-0750",
        "esperado": {
            "qtd_slots": 19,
            "primeiro_inicio": "26/01/2026 03:20",
            "ultimo_fim": "13/02/2026 07:50"
        }
    },
    {
        "id": "CASO_43",
        "desc": "Mix: Dia Único (Início) + Intervalo DLY com Múltiplos Horários",
        "b": "2601051800",
        "c": "2603152130",
        "d": "JAN 05 1800-2130 JAN 06 TIL MAR 15 DLY 0800-1230 1800-2130",
        "esperado": {
            "qtd_slots": 139,
            "primeiro_inicio": "05/01/2026 18:00",
            "ultimo_fim": "15/03/2026 21:30"
        }
    },
    {
        "id": "CASO_44",
        "desc": "Overnight Range: Intervalo longo com barras e horário noturno (2200-1000)",
        "b": "2601072200",
        "c": "2604061000",
        "d": "JAN 07/08 TIL APR 05/06 2200-1000",
        "esperado": {
            "qtd_slots": 89,
            "primeiro_inicio": "07/01/2026 22:00",
            "ultimo_fim": "06/04/2026 10:00"
        }
    },
    {
        "id": "CASO_45",
        "desc": "Multi-Segmento: Mudança de Dias e Horários (JAN-JAN, FEB-APR)",
        "b": "2601100400",
        "c": "2604100759",
        "d": "JAN 10 TIL 16 TUE WED THU FRI SAT 0400-0759 JAN 17 TIL 30 TUE WED THU FRI SAT 0440-0830 FEB 02 TIL APR 10 MON TUE 0500-0759",
        "esperado": {
            "qtd_slots": 35,
            "primeiro_inicio": "10/01/2026 04:00",
            "ultimo_fim": "07/04/2026 07:59"
        }
    },
    {
        "id": "CASO_46",
        "desc": "Multi-Segmento: Filtros de dias não adjacentes (MON SUN / WED THU)",
        "b": "2601110330",
        "c": "2604090759",
        "d": "JAN 11 TIL JAN 26 MON SUN 0330-0759 JAN 28 TIL APR 9 WED THU 0330-0759",
        "esperado": {
            "qtd_slots": 28,
            "primeiro_inicio": "11/01/2026 03:30",
            "ultimo_fim": "09/04/2026 07:59"
        }
    },
    {
        "id": "CASO_47",
        "desc": "Agrupamento Complexo: Listas e Ranges mistos com troca de horário final",
        "b": "2602010440",
        "c": "2603260745",
        "d": "FEB 01 03 TIL 11 MAR 09 TIL 13 0440-0745 23 TIL 26 0450-0745",
        "esperado": {
            "qtd_slots": 19,
            "primeiro_inicio": "01/02/2026 04:40",
            "ultimo_fim": "26/03/2026 07:45"
        }
    },
    {
        "id": "CASO_48",
        "desc": "Mix: Slot Único Inicial + Range Longo com Barras e Horário Longo (18h de duração)",
        "b": "2601172015",
        "c": "2604150400",
        "d": "JAN 17/18 2015-0400 JAN 18/19 TIL APR 14/15 1000-0400",
        "esperado": {
            "qtd_slots": 88,
            "primeiro_inicio": "17/01/2026 20:15",
            "ultimo_fim": "15/04/2026 04:00"
        }
    },
    {
        "id": "CASO_49",
        "desc": "Mix: Slot Único (1744) + Range Longo (NOV-FEB) com Overnight",
        "b": "2511081744",
        "c": "2602050200",
        "d": "NOV 08/09 1744-0200 NOV 09/10 TIL FEB 04/05 1000-0200",
        "esperado": {
            "qtd_slots": 89,
            "primeiro_inicio": "08/11/2025 17:44",
            "ultimo_fim": "05/02/2026 02:00"
        }
    },
    {
        "id": "CASO_50",
        "desc": "Marco Final: Mix de Slot Único + Range Longo (NOV-FEB) com barras e overnight",
        "b": "2511101830",
        "c": "2602080400",
        "d": "NOV 10/11 1830-0400 NOV 11/12 TIL FEB 07/08 1000-0400",
        "esperado": {
            "qtd_slots": 90,
            "primeiro_inicio": "10/11/2025 18:30",
            "ultimo_fim": "08/02/2026 04:00"
        }
    },
    {
        "id": "CASO_51",
        "desc": "Sintaxe Suja: Transição de mês com barra e espaço (30/DEC 01)",
        "b": "2511292041",
        "c": "2602260400",
        "d": "NOV 29/30 2041-0400 30/DEC 01 TIL FEB 25/26 1000-0400",
        "esperado": {
            "qtd_slots": 89,
            "primeiro_inicio": "29/11/2025 20:41",
            "ultimo_fim": "26/02/2026 04:00"  # <--- CORRIGIDO (Era 25/02 10:00)
        }
    },
    {
        "id": "CASO_52",
        "desc": "Sequência Progressiva: Slot Único + Range Mesmo Mês + Range Virada de Ano (DEC-MAR)",
        "b": "2512051712",
        "c": "2603012100",
        "d": "DEC 05 1712-2359 06 TIL 17 0900-2359 DEC 18 TIL MAR 01 0600-2100",
        "esperado": {
            "qtd_slots": 87,
            "primeiro_inicio": "05/12/2025 17:12",
            "ultimo_fim": "01/03/2026 21:00"
        }
        
    },
    {
        "id": "CASO_53",
        "desc": "Transição de Slot Único para Range com barras (Overnight) cruzando o ano (DEC-JAN)",
        "b": "2512071649",
        "c": "2601310100",
        "d": "DEC 07/08 1649-0100 08/09 TIL JAN 30/31 1000-0100",
        "esperado": {
            "qtd_slots": 55,
            "primeiro_inicio": "07/12/2025 16:49",
            "ultimo_fim": "31/01/2026 01:00"
        }
    },
    {
        "id": "CASO_54",
        "desc": "Mix: Slot Único (B) + Range Longo (DEC-MAR) com Overnight diário",
        "b": "2512091859",
        "c": "2603070400",
        "d": "DEC 09/10 1859-0400 10/11 TIL MAR 06/07 1000-0400",
        "esperado": {
            "qtd_slots": 88,
            "primeiro_inicio": "09/12/2025 18:59",
            "ultimo_fim": "07/03/2026 04:00"
        }
    },
    {
        "id": "CASO_55",
        "desc": "Mix: Slot Único (B) + Range Longo (DEC-MAR) com Overnight diário de 18h",
        "b": "2512171650",
        "c": "2603140400",
        "d": "DEC 17/18 1650-0400 18/19 TIL MAR 13/14 1000-0400",
        "esperado": {
            "qtd_slots": 87,
            "primeiro_inicio": "17/12/2025 16:50",
            "ultimo_fim": "14/03/2026 04:00"
        }
    },
    {
        "id": "CASO_56",
        "desc": "Multi-segmento: Listas disjuntas para horários matinais e vespertinos (Dez-Jan)",
        "b": "2512190301",
        "c": "2601280900",
        "d": "DEC 19 TIL 20 29 TIL 31 JAN 01 TIL 03 13 TIL 17 27 TIL 28 0301-0900 DEC 22 TIL 26 JAN 05 TIL 09 19 TIL 23 1700-2100",
        "esperado": {
            "qtd_slots": 30,
            "primeiro_inicio": "19/12/2025 03:01",
            "ultimo_fim": "28/01/2026 09:00"
        }
    },
    {
        "id": "CASO_57",
        "desc": "Densidade Máxima: 4 blocos de horários/meses alternados entre Dez e Jan",
        "b": "2512191300",
        "c": "2601282000",
        "d": "DEC 19 29 TIL 31 1300-2000 DEC 22 TIL 27 0301-0900 JAN 01 02 12 TIL 16 26 TIL 28 1300-2000 06 TIL 10 20 TIL 24 0301-0900",
        "esperado": {
            "qtd_slots": 30,
            "primeiro_inicio": "19/12/2025 13:00",
            "ultimo_fim": "28/01/2026 20:00"
        }
    },
    {
        "id": "CASO_58",
        "desc": "Virada de Ano Crítica: Transição de slot único para range diário no dia 31/Dez",
        "b": "2512301507",
        "c": "2603290400",
        "d": "DEC 30/31 1507-0400 DEC 31/JAN 01 TIL MAR 28/29 1000-0400",
        "esperado": {
            "qtd_slots": 89,
            "primeiro_inicio": "30/12/2025 15:07",
            "ultimo_fim": "29/03/2026 04:00"
        }
    },
    {
        "id": "CASO_59",
        "desc": "Dois blocos diários distintos (Jan e Fev) com um intervalo de 8 dias sem atividade",
        "b": "2601200845",
        "c": "2602271340",
        "d": "JAN 20 TIL 31 0845-1315 FEB 09 TIL 27 0840-1340",
        "esperado": {
            "qtd_slots": 31,
            "primeiro_inicio": "20/01/2026 08:45",
            "ultimo_fim": "27/02/2026 13:40"
        }
    },
    {
        "id": "CASO_60",
        "desc": "Teste de Estresse: Três camadas, overlaps intencionais e filtros semanais",
        "b": "2512012133",
        "c": "2602281630",
        "d": "DEC 01/02 2133-0115 DEC 02 TIL FEB 28 MON TUE THU 0745-1630 WED FRI 1020-1600 SAT 0745-1630 DEC 02 TIL JAN 30 MON/TUE TIL THU/FRI 1940-0115 FRI/SAT 2040-0115",
        "esperado": {
            "qtd_slots": 130,
            "primeiro_inicio": "01/12/2025 21:33",
            "ultimo_fim": "28/02/2026 16:30"
        }
    },
    {
        "id": "CASO_61",
        "desc": "Listas Discretas: Sequências longas de dias específicos com horários alternados",
        "b": "2601051000",
        "c": "2601301550",
        "d": "JAN 05 08 10 12 15 17 19 22 24 26 29 1000-1620 JAN 06 07 09 13 14 16 20 21 23 27 28 30 1000-1550",
        "esperado": {
            "qtd_slots": 23,
            "primeiro_inicio": "05/01/2026 10:00",
            "ultimo_fim": "30/01/2026 15:50"
        }
    },
    {
        "id": "CASO_62",
        "desc": "Horário Solar: DLY SR-SS (0800-2000) com clipping no início pelo Limite B (09:39)",
        "b": "2511280939",
        "c": "2602252218",
        "d": "DLY SR-SS",
        "esperado": {
            "qtd_slots": 90,
            "primeiro_inicio": "28/11/2025 09:39",
            "ultimo_fim": "25/02/2026 20:00"
        }
    },
    {
        "id": "CASO_63",
        "desc": "Regime Híbrido: Transição de slot único para dois turnos diários (SR-SS) entre Jan e Abr",
        "b": "2601131930",
        "c": "2604122104",
        "d": "JAN 13 1930-SS 14 TIL APR 12 SR-1100 1930-SS",
        "esperado": {
            "qtd_slots": 179,
            "primeiro_inicio": "13/01/2026 19:30",
            "ultimo_fim": "12/04/2026 20:00"
        }
    },
    {
        "id": "CASO_64",
        "desc": "Transição: Slot fixo no dia 1 e rotina DLY SR-SS (0800-2000) nos meses seguintes",
        "b": "2601202016",
        "c": "2604192101",
        "d": "JAN 20 2016-2150 21 TIL APR 19 SR-SS",
        "esperado": {
            "qtd_slots": 90,
            "primeiro_inicio": "20/01/2026 20:16",
            "ultimo_fim": "19/04/2026 20:00"
        }
    },
    {
        "id": "CASO_65",
        "desc": "Transição de Ano: Operação parcial SR no dia 1 e rotina DLY SR-SS (0800-2000) até Março",
        "b": "2512031456",
        "c": "2603022134",
        "d": "DEC 03 1456-SS 04 TIL MAR 02 SR-SS",
        "esperado": {
            "qtd_slots": 90,
            "primeiro_inicio": "03/12/2025 14:56",
            "ultimo_fim": "02/03/2026 20:00"
        }
    },
{
        "id": "CASO_66",
        "desc": "Rotina Solar: DLY SR-SS (0800-2000) de Dezembro a Março",
        "b": "2512100833",
        "c": "2603082130",
        "d": "DEC 10 TIL MAR 08 SR-SS",
        "esperado": {
            "qtd_slots": 89,
            "primeiro_inicio": "10/12/2025 08:33",
            "ultimo_fim": "08/03/2026 20:00"
        }
    },
    {
        "id": "CASO_67",
        "desc": "Pernoite Solar: DLY SS-SR (2000-0800) validando offset automático",
        "b": "2601222000",
        "c": "2601260800",
        "d": "DLY SS-SR",
        "esperado": {
            "qtd_slots": 4,
            "primeiro_inicio": "22/01/2026 20:00",
            "ultimo_fim": "26/01/2026 08:00"
        }
    },
    {
        "id": "CASO_68",
        "desc": "Híbrido Solar: Transição de abertura isolada (B) para rotina TIL SR-SS (0800-2000)",
        "b": "2512171958",
        "c": "2603112128",
        "d": "DEC 17 1958-SS DEC 18 TIL MAR 11 SR-SS",
        "esperado": {
            "qtd_slots": 85,
            "primeiro_inicio": "17/12/2025 19:58",
            "ultimo_fim": "11/03/2026 20:00"
        }
    },
    {
        "id": "CASO_69",
        "desc": "Mega Híbrido: Alternância entre horários fixos, datas com barras e rotinas solares (Nov a Jan)",
        "b": "2511081406",
        "c": "2601292220",
        "d": "NOV 08 1406-2151 09 TIL 21 DLY SR-SS 22/23 0938-2155 24 TIL JAN 29 DLY SR-SS",
        "esperado": {
            "qtd_slots": 83,
            "primeiro_inicio": "08/11/2025 14:06",
            "ultimo_fim": "29/01/2026 20:00"
        }
    },
    {
        "id": "CASO_70",
        "desc": "Rotina Solar Pura: DLY SR-SS (0800-2000) com clipping no Limite B (08:51) de Fevereiro a Maio",
        "b": "2602020851",
        "c": "2605012045",
        "d": "DLY SR-SS",
        "esperado": {
            "qtd_slots": 89,
            "primeiro_inicio": "02/02/2026 08:51",
            "ultimo_fim": "01/05/2026 20:00"
        }
    },
    {
        "id": "CASO_71",
        "desc": "Janela Dupla Solar: Descarte do Dia 1 (B pós-SS) e 2 slots diários (SR-1200, 1900-SS) até Março",
        "b": "2512162101",
        "c": "2603152126",
        "d": "DEC 16 2101-SS DEC 17 TIL MAR 15 SR-1200 1900-SS",
        "esperado": {
            "qtd_slots": 179,
            "primeiro_inicio": "17/12/2025 08:00",
            "ultimo_fim": "15/03/2026 20:00"
        }
    },
]