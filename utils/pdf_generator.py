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
        self.cell(30, 10, 'CONA', 0, 0, 'L')
        
        # Títulos Centralizados
        self.set_font('Arial', 'B', 12)
        # Move para a direita para centralizar o título
        self.cell(0, 5, f'MONITORAMENTO NOTAM - {self.turno} {self.data_ref}', 0, 1, 'C')
        
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, 'OBRAS DE FECHAMENTO DE PISTA', 0, 1, 'C')
        
        # Data de Atualização (Abaixo ou à direita)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'Atualizado: {self.data_atualizacao}', 0, 1, 'R')
        
        self.ln(5) # Espaço após o cabeçalho

        # --- CABEÇALHO DA TABELA ---
        self.set_fill_color(240, 240, 240) # Cinza claro
        self.set_font('Arial', 'B', 9)
        
        # Larguras das colunas (Total ~190mm para A4 Retrato)
        # Loc(15), Notam(25), Desc(85), Ini(20), Fim(20), Status(25)
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
    pdf.set_font('Arial', '', 8)

    # Larguras das colunas (devem bater com o header)
    w_loc = 15
    w_notam = 25
    w_desc = 85
    w_ini = 20
    w_fim = 20
    w_status = 25
    
    line_height = 5

    for index, row in df_turno.iterrows():
        # Prepara os textos
        loc = str(row.get('Localidade', ''))
        notam = str(row.get('NOTAM', ''))
        
        # Texto Completo (Item E)
        descricao = str(row.get('Texto', '')).replace('\n', ' ')
        
        # Extrai apenas a HORA dos campos de data para economizar espaço
        # O formato esperado é dd/mm/yyyy hh:mm. Vamos pegar só hh:mm se for o mesmo dia, 
        # mas como o layout pede UTC e é turno, vamos por segurança colocar Hora ou Data curta
        # O layout do PDF mostra "13:00" e "20:00".
        # Vamos tentar extrair a hora da string formatada
        try:
            ini_str = str(row.get('Início Restrição', '')) # ex: 18/11/2025 13:00
            fim_str = str(row.get('Fim Restrição', ''))
            
            # Pega só a hora (últimos 5 chars)
            hora_ini = ini_str[-5:]
            hora_fim = fim_str[-5:]
        except:
            hora_ini = "-"
            hora_fim = "-"

        # Status (Não temos no banco, vamos simular ou deixar em branco conforme layout)
        # O layout mostra "Confirmado" ou "Não Programado". 
        # Vamos assumir "Confirmado" para NOTAMs ativos.
        status = "Confirmado"

        # --- LÓGICA DE CÉLULA MULTILINHA (A PARTE DIFÍCIL DO FPDF) ---
        
        # 1. Calcula quantas linhas a descrição vai ocupar
        # MultiCell simulado para pegar a altura
        # Get string width
        
        # O método mais seguro no FPDF2 é usar multi_cell e salvar a posição Y
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # Testa altura da descrição
        pdf.set_xy(x_start + w_loc + w_notam, y_start)
        pdf.multi_cell(w_desc, line_height, descricao, border=1, align='L', fill=False)
        y_end = pdf.get_y()
        
        # Altura da linha será o máximo entre a descrição e uma linha padrão
        row_height = max(y_end - y_start, line_height)
        
        # Verifica quebra de página
        if y_start + row_height > pdf.h - 15:
            pdf.add_page()
            y_start = pdf.get_y()
            # Recalcula altura se mudou de página (raro dar erro aqui, mas por segurança)
            # Para simplificar, assumimos que cabe ou o add_page resolveu o header.
        
        # Agora desenha as células com a altura fixa calculada (row_height)
        pdf.set_xy(x_start, y_start) # Volta pro começo da linha
        
        pdf.cell(w_loc, row_height, loc, 1, 0, 'C')
        pdf.cell(w_notam, row_height, notam, 1, 0, 'C')
        
        # A descrição precisa ser redesenhada com a altura correta? 
        # O multi_cell já desenhou. Precisamos ter cuidado para não desenhar por cima ou deixar buraco.
        # Estratégia melhor: Desenhar as celulas laterais primeiro, depois o multicell
        
        # Vamos resetar e fazer direito:
        # A melhor forma em FPDF para tabelas com altura variável é salvar Y antes
        
        pdf.set_xy(x_start, y_start) # Reset
        
        # Desenha as células simples
        pdf.cell(w_loc, row_height, loc, 1, 0, 'C')
        pdf.cell(w_notam, row_height, notam, 1, 0, 'C')
        
        # Move cursor para a descrição
        current_x = pdf.get_x()
        pdf.set_xy(current_x, y_start)
        
        # Desenha descrição (MultiCell não aceita height forçada facilmente para preencher, 
        # mas desenha o texto. O border=1 desenha a caixa do tamanho do texto.
        # Para ficar bonito (caixas iguais), desenhamos o Rect em volta depois.
        pdf.multi_cell(w_desc, line_height, descricao, border=0, align='L')
        # Desenha borda da descrição
        pdf.rect(current_x, y_start, w_desc, row_height)
        
        # Move para as células finais
        pdf.set_xy(current_x + w_desc, y_start)
        pdf.cell(w_ini, row_height, hora_ini, 1, 0, 'C')
        pdf.cell(w_fim, row_height, hora_fim, 1, 0, 'C')
        pdf.cell(w_status, row_height, status, 1, 1, 'C') # O último param 1 quebra linha

    # Retorna o binário do PDF
    return pdf.output(dest='S').encode('latin-1', 'replace')