from fpdf import FPDF
from datetime import datetime

class RelatorioPDF(FPDF):
    def __init__(self, turno, data_ref):
        # --- MUDANÇA 1: orientation='L' (Landscape/Paisagem) ---
        super().__init__(orientation='L', format='A4')
        self.turno = turno
        self.data_ref = data_ref
        self.data_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def header(self):
        # Logo / Texto CONA
        self.set_font('Arial', 'B', 16)
        self.cell(30, 10, 'CONA', 0, 0, 'L')
        
        # Títulos Centralizados
        self.set_font('Arial', 'B', 12)
        # Em Landscape a largura total é ~297mm. Cell(0) vai até o fim da margem.
        self.cell(0, 5, f'MONITORAMENTO NOTAM - {self.turno} {self.data_ref}', 0, 1, 'C')
        
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, 'OBRAS DE FECHAMENTO DE PISTA', 0, 1, 'C')
        
        # Data Atualização
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'Atualizado: {self.data_atualizacao}', 0, 1, 'R')
        
        self.ln(5)

        # Cabeçalho da Tabela
        self.set_fill_color(240, 240, 240)
        self.set_font('Arial', 'B', 8)
        
        # --- MUDANÇA 2: NOVAS LARGURAS (Total ~275mm) ---
        # Loc(15), Notam(30), Desc(150), Ini(28), Fim(28), Status(25)
        self.cell(15, 8, 'Loc', 1, 0, 'C', True)
        self.cell(30, 8, 'N NOTAM', 1, 0, 'C', True)
        self.cell(150, 8, 'Descrição', 1, 0, 'L', True) # Coluna bem mais larga!
        self.cell(28, 8, 'Início', 1, 0, 'C', True)
        self.cell(28, 8, 'Fim', 1, 0, 'C', True)
        self.cell(25, 8, 'Status', 1, 1, 'C', True)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

def formatar_data_inteligente(data_hora_str, data_ref_relatorio):
    try:
        if not data_hora_str or len(str(data_hora_str)) < 10:
            return "-"
        
        data_evento = data_hora_str[:10] # dd/mm/yyyy
        hora_evento = data_hora_str[-5:] # HH:MM
        dia_mes = data_hora_str[:5]      # dd/mm
        
        if data_evento == data_ref_relatorio:
            return hora_evento
        else:
            return f"{dia_mes} {hora_evento}"
    except:
        return data_hora_str

def gerar_pdf_turno(df_turno, turno_nome, data_ref_str):
    pdf = RelatorioPDF(turno_nome, data_ref_str)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Arial', '', 8) # Fonte levemente maior pois temos espaço

    # --- DEFINIÇÃO DE LARGURAS (Devem bater com o Header) ---
    w_loc = 15
    w_notam = 30
    w_desc = 150
    w_ini = 28
    w_fim = 28
    w_status = 25
    
    line_height = 6 # Um pouco mais de respiro na altura

    for index, row in df_turno.iterrows():
        loc = str(row.get('Localidade', ''))
        notam = str(row.get('NOTAM', ''))
        descricao = str(row.get('Texto', '')).replace('\n', ' ')
        
        raw_ini = str(row.get('Início Restrição', ''))
        raw_fim = str(row.get('Fim Restrição', ''))
        texto_ini = formatar_data_inteligente(raw_ini, data_ref_str)
        texto_fim = formatar_data_inteligente(raw_fim, data_ref_str)
        status = "Confirmado"

        # --- DESENHO DA TABELA ---
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # --- MUDANÇA 3: QUEBRA DE PÁGINA EM 180mm (A4 Landscape tem 210mm de altura) ---
        if y_start > 180: 
            pdf.add_page()
            y_start = pdf.get_y()
            x_start = pdf.get_x()

        # 1. Mede altura da descrição
        pdf.set_xy(x_start + w_loc + w_notam, y_start)
        pdf.multi_cell(w_desc, line_height, descricao, border=0, align='L')
        
        y_end = pdf.get_y()
        row_height = max(y_end - y_start, line_height)
        
        # 2. Desenha células
        pdf.set_xy(x_start, y_start)
        
        pdf.cell(w_loc, row_height, loc, 1, 0, 'C')
        pdf.cell(w_notam, row_height, notam, 1, 0, 'C')
        
        # Borda Descrição
        pdf.set_xy(x_start + w_loc + w_notam, y_start)
        pdf.rect(pdf.get_x(), pdf.get_y(), w_desc, row_height)
        
        # Colunas Finais
        pdf.set_xy(x_start + w_loc + w_notam + w_desc, y_start)
        pdf.cell(w_ini, row_height, texto_ini, 1, 0, 'C')
        pdf.cell(w_fim, row_height, texto_fim, 1, 0, 'C')
        pdf.cell(w_status, row_height, status, 1, 1, 'C')

    return bytes(pdf.output())