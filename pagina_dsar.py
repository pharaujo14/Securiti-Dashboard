import streamlit as st
from datetime import datetime, timedelta

from utils.auxiliar import filtrar_dados, calcular_tempo_medio
from utils.graficos.graficos_dsar import grafico_tipo_solicitacao, contagemStatus, atendimentosDia, solicitacoesExclusao, tendenciaAtendimentos
from utils.pdf.pdf_generator import gerar_pdf
from utils.logos.import_logos import logo_carrefour, logo_century

# Carregar logos
logo_carrefour()
logo_century()

def pagina_dsar(dados):
    if not dados:
        st.warning("Nenhum dado encontrado.")
        return

    # === FILTROS ===
    orgs_distintas = sorted(set([dado["organizacao"] for dado in dados]))
    org_selecionada = st.sidebar.selectbox('Escolha a Organização', ['Todas'] + orgs_distintas)

    periodo_opcoes = ['Todo o Período', 'Hoje', 'Última Semana', 'Últimos 30 dias', 'Personalizado']
    opcao_selecionada = st.sidebar.selectbox('Escolha o período', periodo_opcoes)

    hoje = datetime.today().date()
    if opcao_selecionada == 'Todo o Período':
        data_inicio = datetime(2024, 1, 1).date()
        data_fim = hoje
    elif opcao_selecionada == 'Hoje':
        data_inicio = hoje
        data_fim = hoje
    elif opcao_selecionada == 'Última Semana':
        data_inicio = hoje - timedelta(days=7)
        data_fim = hoje
    elif opcao_selecionada == 'Últimos 30 dias':
        data_inicio = hoje - timedelta(days=30)
        data_fim = hoje
    elif opcao_selecionada == 'Personalizado':
        data_inicio = st.sidebar.date_input('Data de Início', value=hoje - timedelta(days=30))
        data_fim = st.sidebar.date_input('Data de Fim', value=hoje)

    # Filtragem de dados
    dados_filtrados = filtrar_dados(dados, org_selecionada, data_inicio, data_fim)

    # GRÁFICOS NA TELA PRINCIPAL
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

    # GRÁFICO DE ATENDIMENTOS POR DIA
    st.markdown("<h4 style='text-align: center;'>Atendimentos por Dia (Últimos 30 dias)</h4>", unsafe_allow_html=True)
    img_buffer = atendimentosDia(dados_filtrados)
    if img_buffer:
        st.image(img_buffer)
    else:
        st.write("Sem dados para exibir.")

    # GRÁFICO DE TENDÊNCIA DE ATENDIMENTOS
    st.markdown("<h4 style='text-align: center;'>Linha de Tendência de Atendimentos por Dia</h4>", unsafe_allow_html=True)
    img_buffer = tendenciaAtendimentos(data_inicio, data_fim, dados_filtrados)
    if img_buffer:
        st.image(img_buffer, use_column_width=True)
    else:
        st.write("Sem dados para exibir.")

    # TABELA DE SOLICITAÇÕES
    st.markdown("<h4 style='text-align: center;'>Solicitações</h4>", unsafe_allow_html=True)
    df_tabela = solicitacoesExclusao(dados_filtrados)
    if not df_tabela.empty:
        st.dataframe(df_tabela.set_index('ID'), use_container_width=True)
    else:
        st.write("Nenhuma solicitação de exclusão encontrada.")
        
        # === ESTATÍSTICAS (Sidebar) ===
    with st.sidebar:
        st.markdown("<h3 style='text-align: left;'>Atendimentos</h3>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align: center;'>{len(dados_filtrados)}</h1>", unsafe_allow_html=True)

        tempo_medio_atendimento = calcular_tempo_medio(dados_filtrados)
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