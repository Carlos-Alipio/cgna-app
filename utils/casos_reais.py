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
            "qtd_slots": 122,
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
]