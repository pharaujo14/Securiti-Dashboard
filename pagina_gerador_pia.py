import streamlit as st
import pandas as pd

from utils.auxiliar import sanitize_filename, get_column_value, generate_pdf
from utils.email_utils import enviar_resultado

def gerador_pia():
  st.title("Gerador de PDF do PIA em Preenchimento")
  st.write("Faça upload do CSV para converter para PDF.")

  # Upload do CSV
  uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")

  if uploaded_file:
      df = pd.read_csv(uploaded_file)

      # Gera o nome do arquivo PDF com o primeiro valor da coluna 'Response Option(s)' (PT ou EN)
      first_section_value = get_column_value(df, 'Opção (s) de resposta', 'Response Option(s)', 0, "output")
      sanitized_filename = sanitize_filename(first_section_value)
      pdf_filename = f"{sanitized_filename}.pdf"

      # Gera o PDF usando o logo presente na raiz do projeto
      logo_path = "./utils/logos/logo.png"
      pdf_file = generate_pdf(df, logo_path, pdf_filename)

      # Exibe o botão para download do PDF
      download_button = st.download_button(
          label="Baixar PDF",
          data=open(pdf_file, "rb").read(),
          file_name=pdf_filename,
          mime="application/pdf"
      )

      # Se o download for feito, enviar email com informações
      if download_button:
          st.balloons()

          # Verifica o nome do usuário logado
          username = st.session_state.get('username', 'Desconhecido')

          # Envia o email após o download do PDF
          subject = f"Download realizado por {username}"
          body = f"O usuário {username} realizou o download do arquivo {pdf_filename}."

          # Configurações de email

          # Define o remetente e o destinatário
          sender = st.secrets['smtp']['sender']
          recipient = st.secrets['smtp']['recipient']
          password = st.secrets['smtp']['password']

          # Função de envio de email permanece igual
          enviar_resultado(subject, body, sender, [recipient], password)
