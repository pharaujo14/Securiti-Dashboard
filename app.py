import streamlit as st
import pandas as pd
import pytz

from PIL import Image
from datetime import datetime
from datetime import timedelta
from streamlit_autorefresh import st_autorefresh

from conectaBanco import conectaBanco
from cadastra_user import trocar_senha, adicionar_usuario
from login import login, is_authenticated
from api import atualizar_dados, buscar_dados
from auxiliar import obter_ultima_atualizacao, filtrar_dados, calcular_tempo_medio
from graficos import grafico_tipo_solicitacao, contagemStatus, atendimentosDia, solicitacoesExclusao, tendenciaAtendimentos
from pdf_generator import gerar_pdf


# Verifica se o usuário está autenticado
if not is_authenticated():
    login()
    st.stop()

# Verifica a role do usuário logado
user_role = st.session_state.get('role', '')

# Carregar credenciais do banco de dados
db_user = st.secrets["database"]["user"]
db_password = st.secrets["database"]["password"]

# Conexão com o banco de dados
collection = conectaBanco(db_user, db_password)

# Carregar logos
logo_carrefour = Image.open("logo.png")
logo_century = Image.open("logo_century.png")

# Configurações da página com o logo
st.set_page_config(page_title="Century Data", page_icon="Century_mini_logo-32x32.png", layout="wide")

# Atualizar a cada 5 minutos (300 segundos)
count = st_autorefresh(interval=300000, key="data_refresh")

# Conectar à collection de histórico de atualizações
collection_historico = conectaBanco(db_user, db_password)['historico_atualizacoes']

# Definir as colunas da primeira linha do layout
col1, col2, col3 = st.columns([1, 3, 1])

# Exibir os logos e o título na primeira linha
with col1:
    st.image(logo_carrefour, width=150)

with col2:
    st.markdown("<h1 style='text-align: center; color: black;'>Atendimento da Central de Privacidade</h1>", unsafe_allow_html=True)

with col3:
    st.image(logo_century, width=150)

# Linha separadora vermelha para o "Atendimento"
st.markdown("<hr style='border:3px solid red'>", unsafe_allow_html=True)

# Filtros e seleção de período
with st.sidebar:
    
    st.image(logo_century, width=150)

    atualizar_dados(collection, collection_historico)

    dados = buscar_dados(collection)  # Inicializa dados antes do botão

    # Exibir a última atualização
    ultima_atualizacao = obter_ultima_atualizacao(collection_historico)
    st.write(f"Última atualização: {ultima_atualizacao}")

    # Uso da variável dados
    if dados:  # Verifica se há dados

        # Obter todas as organizações distintas (org_unit_name) para o filtro
        orgs_distintas = sorted(set([dado["organizacao"] for dado in dados]))
        org_selecionada = st.selectbox('Escolha a Organização', ['Todas'] + orgs_distintas)

        # Opções de período para a consulta
        periodo_opcoes = ['Todo o Período','Hoje', 'Última Semana', 'Últimos 30 dias', 'Personalizado']
        opcao_selecionada = st.selectbox('Escolha o período', periodo_opcoes)

        # Lógica para definir as datas de início e fim
        hoje = datetime.today().date()  # Convertendo para datetime.date
        if opcao_selecionada == 'Todo o Período':
            data_inicio = datetime(2024, 1, 1).date()  # Definindo a data de início como 01/01/2024
            data_fim = hoje
        if opcao_selecionada == 'Hoje':
            data_inicio = hoje
            data_fim = hoje
        elif opcao_selecionada == 'Última Semana':
            data_inicio = hoje - timedelta(days=7)
            data_fim = hoje
        elif opcao_selecionada == 'Últimos 30 dias':
            data_inicio = hoje - timedelta(days=30)
            data_fim = hoje
        elif opcao_selecionada == 'Personalizado':
            # Escolha da data de início
            data_inicio = st.date_input('Data de Início', value=hoje - timedelta(days=30))
            
            # Definir o valor padrão para a data de fim como hoje
            data_fim_default = hoje  # Ambos agora são do tipo date
            
            # Ajustar o campo de data de fim, sem limite
            data_fim = st.date_input('Data de Fim', value=data_fim_default)  # Removido o max_value
        
    else:
        st.warning("Nenhum dado encontrado.")

# Filtrar os dados pela organização e período selecionados
dados_filtrados = filtrar_dados(dados, org_selecionada, data_inicio, data_fim)

# Exibir a contagem total de atendimentos filtrados
atendimentos_totais = len(dados_filtrados)

tempo_medio_atendimento = calcular_tempo_medio(dados_filtrados)

# Caixa com o total de atendimentos
with st.sidebar:
    st.markdown("<h3 style='text-align: left;'>Atendimentos</h3>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center;'>{atendimentos_totais}</h1>", unsafe_allow_html=True)

    st.markdown("<h3 style='text-align: left;'>Tempo Médio de Atendimento (dias)</h3>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center;'>{tempo_medio_atendimento}</h1>", unsafe_allow_html=True)

    if st.button("Gerar PDF", key="generate"):
        with st.spinner("Gerando o PDF..."):
            pdf_content = gerar_pdf(data_inicio, data_fim, dados_filtrados, org_selecionada)
                        
            st.download_button(
                label="Download do relatório PDF",
                data=pdf_content,
                file_name="relatorio_atendimento.pdf",
                mime="application/pdf",
                key="download",
            )

    # Definindo uma flag de sessão para mostrar o formulário de troca de senha
    if 'mostrar_form_troca_senha' not in st.session_state:
        st.session_state.mostrar_form_troca_senha = False

    if st.button("Trocar Senha"):
        st.session_state.mostrar_form_troca_senha = not st.session_state.mostrar_form_troca_senha

    if st.session_state.mostrar_form_troca_senha:
        trocar_senha()

    if user_role == "admin":
        if 'mostrar_form_criar_user' not in st.session_state:
            st.session_state.mostrar_form_criar_user = False

        if st.button("Novo usuário"):
            st.session_state.mostrar_form_criar_user = not st.session_state.mostrar_form_criar_user

        if st.session_state.mostrar_form_criar_user:
            adicionar_usuario()

# Colocar os gráficos lado a lado
col1, col2 = st.columns(2)

with col1:
    st.markdown("<h4 style='text-align: center;'>Tipo de Solicitação</h4>", unsafe_allow_html=True)
    img_buffer = grafico_tipo_solicitacao(dados_filtrados)
    
    if img_buffer:
        st.image(img_buffer, use_column_width=True)
    else:
        st.write("Sem dados para exibir.")

with col2:
    st.markdown("<h4 style='text-align: center;'>Contagem de Status</h4>", unsafe_allow_html=True)
    img_buffer = contagemStatus(dados_filtrados)
    
    if img_buffer:
        st.image(img_buffer, use_column_width=True)
    else:
        st.write("Sem dados para exibir.")

# Gráfico de Atendimentos por Dia
st.markdown("<h4 style='text-align: center;'>Atendimentos por Dia (Últimos 30 dias)</h4>", unsafe_allow_html=True)

img_buffer = atendimentosDia(dados_filtrados)

if img_buffer:
    st.image(img_buffer)
else:
    st.write("Sem dados para exibir.")

# Gráfico de Linha de Tendência de Atendimentos por Dia
st.markdown("<h4 style='text-align: center;'>Linha de Tendência de Atendimentos por Dia</h4>", unsafe_allow_html=True)

img_buffer = tendenciaAtendimentos(data_inicio, data_fim, dados_filtrados)

if img_buffer:
    st.image(img_buffer, use_column_width=True)
else:
    st.write("Sem dados para exibir.")

# Solicitações de Atendimentos por Dia
st.markdown("<h4 style='text-align: center;'>Solicitações</h4>", unsafe_allow_html=True)

df_tabela = solicitacoesExclusao(dados_filtrados)

if not df_tabela.empty:
    st.dataframe(df_tabela.set_index('ID'), use_container_width=True)
else:
    st.write("Nenhuma solicitação de exclusão encontrada.")