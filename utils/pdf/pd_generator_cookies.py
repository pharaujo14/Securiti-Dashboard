from fpdf import FPDF
from datetime import datetime
import tempfile
import os
import pytz

from utils.graficos.graficos_cookies_export import gerar_grafico_consents_img, gerar_grafico_categorias_img, gerar_grafico_paises_img, gerar_grafico_dominios_img

class PDFCookies(FPDF):
    def __init__(self, logo_carrefour, logo_century):
        fuso_horario_brasilia = pytz.timezone("America/Sao_Paulo")
        data_atualizacao_brasilia = datetime.now(fuso_horario_brasilia)
        hora_formatada = data_atualizacao_brasilia.strftime('%d/%m/%Y %H:%M')

        super().__init__()
        self.logo_carrefour = logo_carrefour
        self.logo_century = logo_century
        self.gerado_em = hora_formatada

    def header(self):
        self.image(self.logo_carrefour, 10, 8, 33)
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Relatório de Cookies", 0, 1, "C")
        self.image(self.logo_century, 170, 8, 33)
        self.ln(15)

        self.set_draw_color(255, 0, 0)
        self.set_line_width(1)
        self.line(10, 28, 200, 28)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 7)
        self.cell(0, 10, f"Página {self.page_no()} - Gerado em {self.gerado_em}", 0, 0, "R")

    def add_report_info(self, data_inicio, data_fim, org_selecionada):
        col_width = 60
        row_height = 6

        self.set_font("Arial", "B", 10)
        self.cell(col_width, row_height, "Data de início", 1, 0, 'L')
        self.cell(col_width, row_height, "Data de fim", 1, 0, 'L')
        self.cell(col_width, row_height, "Organização Selecionada", 1, 1, 'L')

        self.set_font("Arial", "", 10)
        self.cell(col_width, row_height, str(data_inicio), 1, 0, 'L')
        self.cell(col_width, row_height, str(data_fim), 1, 0, 'L')
        self.cell(col_width, row_height, str(org_selecionada), 1, 1, 'L')

        self.ln(10)  # Aumentei o espaçamento aqui

    def add_chart(self, title, img_buffer):
        # Verifica se precisa de nova página considerando altura do gráfico + título + espaçamento
        if self.get_y() + 110 > self.page_break_trigger:  # Aumentei a margem de segurança
            self.add_page()
            self.set_y(40)  # Posição após o cabeçalho

        self.ln(10)  # Aumentei o espaçamento antes do título
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, title, 0, 1, "C")
        self.ln(5)  # Espaçamento entre título e gráfico

        if img_buffer:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(img_buffer.getvalue())
                tmp_file_path = tmp_file.name

            y_inicial = self.get_y()
            # Reduzi um pouco a largura para garantir que caiba na página
            self.image(tmp_file_path, x=15, y=y_inicial, w=170)  # Diminuí de 180 para 170
            self.set_y(y_inicial + 90)  # Mantém a altura do gráfico
            os.remove(tmp_file_path)
        else:
            self.cell(0, 10, "Não há dados suficientes para gerar o gráfico.", 0, 1, "C")

        self.ln(15)  # Aumentei o espaçamento após o gráfico


def gerar_pdf_cookies(data_inicio, data_fim, df_filtrado, org_selecionada, logo_carrefour="./utils/logos/logo.png", logo_century="./utils/logos/logo_century.png"):
    pdf = PDFCookies(logo_carrefour, logo_century)
    pdf.add_page()
    pdf.add_report_info(data_inicio, data_fim, org_selecionada)

    # Adiciona os gráficos com ordenação decrescente (já deve ser tratado nas funções de gráfico)
    pdf.add_chart("Domínios mais Acessados (Top 10)", gerar_grafico_dominios_img(df_filtrado))
    pdf.add_chart("Categorias de Cookies por Domínio (Top 5)", gerar_grafico_categorias_img(df_filtrado))
    pdf.add_chart("Distribuição de Países (Top 10)", gerar_grafico_paises_img(df_filtrado))
    pdf.add_chart("Total de Consents por Organização", gerar_grafico_consents_img(df_filtrado))

    pdf_output = pdf.output(dest="S").encode("latin1")
    return pdf_output