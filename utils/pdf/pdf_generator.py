from fpdf import FPDF
from datetime import datetime
from utils.graficos.graficos_dsar import grafico_tipo_solicitacao, contagemStatus, atendimentosDia, solicitacoesExclusao, tendenciaAtendimentos

import tempfile
import os
import pytz

# Classe personalizada para geração do PDF
class PDF(FPDF):
    def __init__(self, logo_carrefour, logo_century):

        fuso_horario_brasilia = pytz.timezone("America/Sao_Paulo")
        data_atualizacao_brasilia = datetime.now(fuso_horario_brasilia)
        data_atualizacao_utc = data_atualizacao_brasilia.astimezone(pytz.utc)  # Converte para UTC
        hora_formatada = data_atualizacao_brasilia.strftime('%d/%m/%Y %H:%M')

        super().__init__()
        self.logo_carrefour = logo_carrefour
        self.logo_century = logo_century
        self.gerado_em = hora_formatada

    def header(self):
        # Exibir os logos e o título na primeira linha
        self.image(self.logo_carrefour, 10, 8, 33)  # Logo à esquerda
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Atendimento da Central de Privacidade", 0, 1, "C")  # Título centralizado
        self.image(self.logo_century, 170, 8, 33)  # Logo à direita
        self.ln(15)
        
        # Linha separadora vermelha
        self.set_draw_color(255, 0, 0)  # Vermelho
        self.set_line_width(1)
        self.line(10, 28, 200, 28)

    def footer(self):
        # Definir posição no rodapé
        self.set_y(-15)
        self.set_font("Arial", "I", 7)
        self.cell(0, 10, f"Gerado em {self.gerado_em}", 0, 0, "R")  # Texto centralizado no rodapé

    def add_report_info(self, data_inicio, data_fim, org_selecionada):
        # Definindo as larguras das colunas
        col_width = 60  # Largura de cada coluna (ajuste conforme necessário)
        row_height = 6  # Altura das linhas

        # Definir a fonte para os cabeçalhos
        self.set_font("Arial", "B", 10)

        # Linha de cabeçalhos
        self.cell(col_width, row_height, "Data de início", 1, 0, 'L')
        self.cell(col_width, row_height, "Data de fim", 1, 0, 'L')
        self.cell(col_width, row_height, "Organização Selecionada", 1, 1, 'L')

        # Definir a fonte para os valores
        self.set_font("Arial", "", 10)

        # Linha de valores
        self.cell(col_width, row_height, str(data_inicio), 1, 0, 'L')
        self.cell(col_width, row_height, str(data_fim), 1, 0, 'L')
        self.cell(col_width, row_height, str(org_selecionada), 1, 1, 'L')

        self.ln(5)  # Espaço após a tabela

    def add_grafico_tipo_solicitacao(self, dados_filtrados):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Tipo de Solicitação", 0, 1, "C")
        self.ln(5)

        img_buffer = grafico_tipo_solicitacao(dados_filtrados)
        if img_buffer:
            # Criar um arquivo temporário para salvar a imagem do gráfico
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(img_buffer.getvalue())
                tmp_file_path = tmp_file.name

            # Adicionar a imagem ao PDF
            self.image(tmp_file_path, x=10, y=self.get_y(), w=150)

            # Remover o arquivo temporário após o uso
            os.remove(tmp_file_path)

            self.ln(75)
        else:
            self.cell(0, 10, "Não há dados suficientes para gerar o gráfico.", 0, 1, "C")

    def add_grafico_contagemStatus(self, dados_filtrados):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Contagem de Status", 0, 1, "C")
        self.ln(5)

        img_buffer = contagemStatus(dados_filtrados)
        if img_buffer:
            # Criar um arquivo temporário para salvar a imagem do gráfico
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(img_buffer.getvalue())
                tmp_file_path = tmp_file.name

            # Adicionar a imagem ao PDF
            self.image(tmp_file_path, x=10, y=self.get_y(), w=150)

            # Remover o arquivo temporário após o uso
            os.remove(tmp_file_path)

            self.ln(75)
        else:
            self.cell(0, 10, "Não há dados suficientes para gerar o gráfico.", 0, 1, "C")

    def add_grafico_atendimentosDia(self, dados_filtrados):
        
        self.ln(5)
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Atendimentos por Dia (Últimos 30 dias)", 0, 1, "C")
        self.ln(5)

        img_buffer = atendimentosDia(dados_filtrados)
        if img_buffer:
            # Criar um arquivo temporário para salvar a imagem do gráfico
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(img_buffer.getvalue())
                tmp_file_path = tmp_file.name

            # Ajuste de proporção para evitar achatamento
            self.image(tmp_file_path, x=30, y=self.get_y(), w=150, h=80)

            # Remover o arquivo temporário após o uso
            os.remove(tmp_file_path)

            self.ln(85)  # Ajuste a altura da linha conforme necessário
        else:
            self.cell(0, 10, "Não há dados suficientes para gerar o gráfico.", 0, 1, "C")

    def add_tabela_exclusao(self, df_tabela):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Solicitações", 0, 1, "C")
        self.ln(5)

        self.set_font("Arial", "B", 7)

        # Cabeçalho da tabela
        headers = df_tabela.columns.tolist()
        colunas_largura = [10, 40, 65, 25, 20, 15, 20]  # Ajuste as larguras conforme necessário

        # Adicionar cabeçalho com bordas
        for header, largura in zip(headers, colunas_largura):
            self.cell(largura, 7, header, 1, 0, 'C')
        self.ln()

        # Adicionar dados da tabela
        self.set_font("Arial", "", 6)
        for _, row in df_tabela.iterrows():
            # Checa se há espaço suficiente na página para a linha
            if self.get_y() + 6 > self.page_break_trigger:
                self.add_page()
                self.set_font("Arial", "B", 6)
                for header, largura in zip(headers, colunas_largura):
                    self.cell(largura, 6, header, 1, 0, 'C')
                self.ln()
                self.set_font("Arial", "", 6)

            # Limita cada célula a 50 caracteres e adiciona bordas
            for header, largura in zip(headers, colunas_largura):
                cell_text = str(row[header])[:40]  # Limita a 50 caracteres
                self.cell(largura, 6, cell_text, 1, 0, 'C')  # 1 adiciona a borda
            self.ln()  # Move para a próxima linha

        self.ln(5)  # Espaço após a tabela

    def add_grafico_tendenciaAtendimentos(self, data_inicio, data_fim, dados_filtrados):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Linha de Tendência de Atendimentos por Dia", 0, 1, "C")
        self.ln(5)

        img_buffer = tendenciaAtendimentos(data_inicio, data_fim, dados_filtrados)
        if img_buffer:
            # Criar um arquivo temporário para salvar a imagem do gráfico
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(img_buffer.getvalue())
                tmp_file_path = tmp_file.name

            # Ajuste de proporção para evitar achatamento
            self.image(tmp_file_path, x=30, y=self.get_y(), w=150, h=80)

            # Remover o arquivo temporário após o uso
            os.remove(tmp_file_path)

            self.ln(85)  # Ajuste a altura da linha conforme necessário
        else:
            self.cell(0, 10, "Não há dados suficientes para gerar o gráfico.", 0, 1, "C")

    def _add_bold_label(self, label, text):
        # Adicionar o título em negrito
        self.set_font("Arial", "B", 12)
        self.cell(self.get_string_width(label) + 2, 10, label, 0, 0)
        
        # Adicionar o conteúdo em fonte normal
        self.set_font("Arial", "", 12)
        self.cell(0, 10, str(text), 0, 1)


# Função para gerar o PDF
def gerar_pdf(data_inicio, data_fim, dados_filtrados, org_selecionada, logo_carrefour="logo.png", logo_century="logo_century.png"):
    pdf = PDF(logo_carrefour, logo_century)
    pdf.add_page()
    pdf.add_report_info(data_inicio, data_fim, org_selecionada)

    # Função para verificar se o gráfico vai caber na página, se não, adicionar uma nova página
    def verificar_espaco_pdf(pdf, altura_necessaria):
        if pdf.get_y() + altura_necessaria > pdf.h - pdf.b_margin:  # Considera a margem inferior
            pdf.add_page()  # Adiciona nova página se não houver espaço suficiente

    # Exemplo de uso para verificar o espaço antes de cada gráfico
    verificar_espaco_pdf(pdf, altura_necessaria=80)  # Altura estimada para o gráfico
    pdf.add_grafico_tipo_solicitacao(dados_filtrados)
    pdf.ln(10)  # Adiciona um espaço de 10 mm após o gráfico
   
    verificar_espaco_pdf(pdf, altura_necessaria=80)
    pdf.add_grafico_contagemStatus(dados_filtrados)
    pdf.ln(10)  # Adiciona um espaço de 10 mm após o gráfico
    
    verificar_espaco_pdf(pdf, altura_necessaria=80)
    pdf.add_grafico_atendimentosDia(dados_filtrados)
    pdf.ln(10)  # Adiciona um espaço de 10 mm após o gráfico

    # Adicionar o último gráfico com verificação de espaço
    verificar_espaco_pdf(pdf, altura_necessaria=80)
    pdf.add_grafico_tendenciaAtendimentos(data_inicio, data_fim, dados_filtrados)

    verificar_espaco_pdf(pdf, altura_necessaria=40)
    df_tabela = solicitacoesExclusao(dados_filtrados)
    if not df_tabela.empty:
        pdf.add_tabela_exclusao(df_tabela) 
    else:
        pdf.cell(0, 10, "Nenhuma solicitação de exclusão encontrada.", 0, 1, "C")

    # Gerar o PDF final
    pdf_output = pdf.output(dest="S").encode("latin1")
    return pdf_output
