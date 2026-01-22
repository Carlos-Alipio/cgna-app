from datetime import datetime

# Lista de Casos que JÁ FUNCIONAM e não podem quebrar
# Estrutura: Input (B, C, D) + Output Esperado (Snapshot)

CASOS_BLINDADOS = [
    {
        "id": "CASO_01",
        "desc": "DLY Simples (26/01 a 13/02)",
        "b": "2601260320",
        "c": "2602130750",
        "d": "DLY 0320-0750",
        # O que esperamos? 19 dias consecutivos
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
        # O que esperamos? 4 + 1 + 1 + 1 = 7 slots específicos
        "esperado": {
            "qtd_slots": 7,
            "primeiro_inicio": "20/01/2026 11:00",
            "ultimo_fim": "30/01/2026 19:00" # O último cronológico é dia 30
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

]