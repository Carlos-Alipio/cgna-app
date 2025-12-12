from fpdf import FPDF
from datetime import datetime

class RelatorioPDF(FPDF):
    def __init__(self, turno, data_ref):
        super().__init__()
        self.turno = turno
        self.data_ref = data_ref
        self.data_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def header(self):
        # Logo / Texto CONA (Canto Superior Esquerdo)
        self.set_font('Arial', 'B', 16)
        self.cell(30, 10, 'CGNA', 0, 0, 'L')
        
        # Títulos Centralizados
        self.set_font('Arial', 'B', 12)
        # Move para a direita para centralizar o título
        self.cell(0, 5, f'MONITORAMENTO NOTAM - {self.turno} {self.data_ref}', 0, 1, 'C')
        
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, 'OBRAS DE FECHAMENTO DE PISTA', 0, 1, 'C')
        
        # Data de Atualização
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'Atualizado: {self.data_atualizacao}', 0, 1, 'R')
        
        self.ln(5) # Espaço após o cabeçalho

        # --- CABEÇALHO DA TABELA ---
        self.set_fill_color(240, 240, 240) # Cinza claro
        self.set_font('Arial', 'B', 8)
        
        # Larguras das colunas
        # Loc(15), Notam(25), Desc(85), Ini(20), Fim(20), Status(25) = Total 190
        self.cell(15, 8, 'Loc', 1, 0, 'C', True)
        self.cell(25, 8, 'N NOTAM', 1, 0, 'C', True)
        self.cell(85, 8, 'Descrição', 1, 0, 'L', True)
        self.cell(20, 8, 'Início', 1, 0, 'C', True)
        self.cell(20, 8, 'Fim', 1, 0, 'C', True)
        self.cell(25, 8, 'Status', 1, 1, 'C', True)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

def gerar_pdf_turno(df_turno, turno_nome, data_ref_str):
    """
    Gera o PDF com base no DataFrame do turno filtrado.
    """
    pdf = RelatorioPDF(turno_nome, data_ref_str)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Arial', '', 7) # Fonte menor para caber texto

    # Larguras das colunas
    w_loc = 15
    w_notam = 25
    w_desc = 85
    w_ini = 20
    w_fim = 20
    w_status = 25
    
    line_height = 5 # Altura mínima da linha

    for index, row in df_turno.iterrows():
        # Prepara os textos
        loc = str(row.get('Localidade', ''))
        notam = str(row.get('NOTAM', ''))
        descricao = str(row.get('Texto', '')).replace('\n', ' ')
        
        # Extrai apenas a HORA dos campos de data
        try:
            # Formato esperado: dd/mm/yyyy hh:mm
            # Pega os últimos 5 chars (HH:MM)
            ini_str = str(row.get('Início Restrição', '')) 
            fim_str = str(row.get('Fim Restrição', ''))
            
            hora_ini = ini_str[-5:] if len(ini_str) > 5 else ini_str
            hora_fim = fim_str[-5:] if len(fim_str) > 5 else fim_str
        except:
            hora_ini = "-"
            hora_fim = "-"

        status = "Confirmado"

        # --- LÓGICA DE TABELA COM ALTURA DINÂMICA ---
        
        # 1. Salva posição inicial
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # 2. Verifica se precisamos quebrar página ANTES de desenhar
        # Simula a altura da descrição
        pdf.set_xy(x_start + w_loc + w_notam, y_start)
        # MultiCell retorna None, precisamos calcular altura na mão ou confiar no FPDF2
        # FPDF2 moderno não tem GetMultiCellHeight fácil exposto, vamos usar uma heurística segura:
        # Se estiver muito perto do fim da página (ex: 20mm), pula.
        if y_start > 270: 
            pdf.add_page()
            y_start = pdf.get_y() # Atualiza novo Y
            x_start = pdf.get_x()

        # 3. Desenha a Descrição (MultiCell) para saber a altura real da linha
        # Movemos para a coluna da descrição
        pdf.set_xy(x_start + w_loc + w_notam, y_start)
        pdf.multi_cell(w_desc, line_height, descricao, border=0, align='L')
        
        # Pega onde o cursor parou (Y final da descrição)
        y_end = pdf.get_y()
        row_height = max(y_end - y_start, line_height)
        
        # 4. Desenha as bordas e as outras células com a altura calculada
        pdf.set_xy(x_start, y_start) # Volta para o início da linha
        
        pdf.cell(w_loc, row_height, loc, 1, 0, 'C')
        pdf.cell(w_notam, row_height, notam, 1, 0, 'C')
        
        # Desenha apenas a Borda da descrição (o texto já foi desenhado)
        pdf.set_xy(x_start + w_loc + w_notam, y_start)
        pdf.rect(pdf.get_x(), pdf.get_y(), w_desc, row_height)
        
        # Move para as colunas finais
        pdf.set_xy(x_start + w_loc + w_notam + w_desc, y_start)
        pdf.cell(w_ini, row_height, hora_ini, 1, 0, 'C')
        pdf.cell(w_fim, row_height, hora_fim, 1, 0, 'C')
        pdf.cell(w_status, row_height, status, 1, 1, 'C') # O '1' no final quebra a linha

    # --- CORREÇÃO DO ERRO ---
    # FPDF2 moderno retorna bytearray direto no output().
    # Não usamos .encode()
    return bytes(pdf.output())