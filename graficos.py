import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import altair as alt

from matplotlib.ticker import MaxNLocator
from matplotlib.dates import DateFormatter
from datetime import datetime, timedelta


# Dicionário de tradução dos valores de type_tags
traducoes = {
    "rectify": "Correção",
    "erasure": "Eliminação",
    "object": "Contestação/Objeção",
    "restrict-process": "Revogação de Consentimento",
    "access": "Confirmação de Tratamento de Dados",
    "restrict-auto-decision": "Revisão de Decisões Automatizadas"
}

def grafico_tipo_solicitacao(dados_filtrados):
    """Gera e exibe o gráfico de Tipo de Solicitação no Streamlit."""
    
    # Contagem dos tipos de solicitação com base no type_tags
    tipos_solicitacao = [traducoes[dado["type_tags"]] for dado in dados_filtrados if dado["type_tags"] in traducoes]
    df_tipos_solicitacao = pd.DataFrame(tipos_solicitacao, columns=["Tipo de Solicitação"])
    contagem_tipos = df_tipos_solicitacao["Tipo de Solicitação"].value_counts()

    st.markdown("<h4 style='text-align: center;'>Tipo de Solicitação</h4>", unsafe_allow_html=True)

    if not contagem_tipos.empty:
        # Criar um DataFrame para o Seaborn
        df_contagem_tipos = contagem_tipos.reset_index()
        df_contagem_tipos.columns = ['Tipo de Solicitação', 'Quantidade']

        # Criar o gráfico de barras com Seaborn
        plt.figure(figsize=(10, 6))
        sns.barplot(x='Quantidade', y='Tipo de Solicitação', data=df_contagem_tipos, color='#0000CD')

        # Adicionar os valores fora das barras
        for i, v in enumerate(df_contagem_tipos['Quantidade']):
            plt.text(v + 1, i, f'{v}', color='black', va='center', fontweight='bold')

        # Ajustar limites do gráfico
        plt.xlim(0, df_contagem_tipos['Quantidade'].max() + 5)

        # Remover rótulos dos eixos
        plt.xlabel('')
        plt.ylabel('')

        sns.despine()
        plt.grid(False)
        st.pyplot(plt)
    else:
        st.write("Sem dados para exibir.")

def contagemStatus(dados_filtrados):
    # Gráfico de Status
    st.markdown("<h4 style='text-align: center;'>Contagem de Status</h4>", unsafe_allow_html=True)

    status_solicitacao = [dado["status"] for dado in dados_filtrados]
    df_status_solicitacao = pd.DataFrame(status_solicitacao, columns=["Status"])
    contagem_status = df_status_solicitacao["Status"].value_counts()

    if not contagem_status.empty:
        df_contagem_status = contagem_status.reset_index()
        df_contagem_status.columns = ['Status', 'Quantidade']

        plt.figure(figsize=(10, 6))
        sns.barplot(x='Quantidade', y='Status', data=df_contagem_status, color='#0000CD')

        for i, v in enumerate(df_contagem_status['Quantidade']):
            plt.text(v + 1, i, f'{v}', color='black', va='center', fontweight='bold')

        plt.xlim(0, df_contagem_status['Quantidade'].max() + 5)
        plt.xlabel('')
        plt.ylabel('')
        sns.despine()
        plt.grid(False)
        st.pyplot(plt)
    else:
        st.write("Sem dados para exibir.")

def atendimentosDia(dados_filtrados):
    # Gráfico de Atendimentos por Dia
    st.markdown("<h4 style='text-align: center;'>Atendimentos por Dia (Últimos 30 dias)</h4>", unsafe_allow_html=True)

    # Extrair datas de atendimento (timestamp ou string) e verificar o tipo de dado
    datas_atendimento = [dado["created_at"] for dado in dados_filtrados]
    df_atendimentos = pd.DataFrame(datas_atendimento, columns=["Data de Atendimento"])

    # Tentar converter primeiro como timestamp em milissegundos
    try:
        # Caso os dados sejam timestamps
        df_atendimentos['Data de Atendimento'] = pd.to_datetime(df_atendimentos['Data de Atendimento'], unit='ms')
    except ValueError:
        # Caso os dados sejam strings no formato DD/MM/AAAA HH:MM:SS
        df_atendimentos['Data de Atendimento'] = pd.to_datetime(df_atendimentos['Data de Atendimento'], format='%d/%m/%Y %H:%M:%S')

    # Contar atendimentos por dia
    contagem_atendimentos_por_dia = df_atendimentos['Data de Atendimento'].dt.date.value_counts().sort_index()

    # Se houver dados de atendimento
    if not contagem_atendimentos_por_dia.empty:
        # Transformar a contagem em DataFrame
        df_contagem_dia = contagem_atendimentos_por_dia.reset_index()
        df_contagem_dia.columns = ['Data', 'Quantidade']

        # Criar uma sequência de datas que cobre o intervalo completo
        full_range = pd.date_range(start=df_atendimentos['Data de Atendimento'].min().date(),
                                end=df_atendimentos['Data de Atendimento'].max().date(), 
                                freq='D')

        # Reindexar o DataFrame para preencher os dias faltantes com zero
        df_contagem_dia = df_contagem_dia.set_index('Data').reindex(full_range, fill_value=0).reset_index()
        df_contagem_dia.columns = ['Data', 'Quantidade']

        # Selecionar apenas os últimos 30 dias do intervalo
        df_contagem_dia = df_contagem_dia.tail(30)

        # Converter a coluna 'Data' para o formato DD-MM para o eixo X
        df_contagem_dia['Data'] = df_contagem_dia['Data'].dt.strftime('%d-%m')

        # Criar o gráfico de barras
        fig, ax = plt.subplots(figsize=(12, 6))  # Criar figura e eixos
        sns.barplot(x='Data', y='Quantidade', data=df_contagem_dia, color='#0000CD', ax=ax)

        # Adicionar os valores fora das barras
        for i, v in enumerate(df_contagem_dia['Quantidade']):
            ax.text(i, v + 0.5, f'{v}', color='black', ha='center', fontweight='bold')

        # Rotacionar rótulos do eixo X para melhor visualização
        plt.xticks(rotation=45)

        # Remover rótulos e título
        ax.set_ylabel('')  # Remover o rótulo do eixo Y
        ax.set_xlabel('')  # Remover o rótulo do eixo X
        sns.despine()
        plt.grid(False)

        # Configurar os ticks do eixo Y para serem inteiros
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        # Exibir o gráfico no Streamlit
        st.pyplot(fig)

    else:
        st.write("Sem dados para exibir.")

def solicitacoesExclusao(dados_filtrados):
    # Criar uma seção para o título e a tabela de exclusão
    st.markdown("<h4 style='text-align: center;'>Solicitações de Exclusão</h4>", unsafe_allow_html=True)

    # Filtrar apenas os tickets de exclusão ('type_tags': 'erasure')
    tickets_exclusao = [ticket for ticket in dados_filtrados if 'erasure' in ticket["type_tags"]]

    # Preparar os dados da tabela
    tabela_dados = []

    for ticket in tickets_exclusao:
        # Tentar converter created_at e published_at para datetime
        created_at = pd.to_datetime(ticket['created_at'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        published_at = pd.to_datetime(ticket.get('published_at'), format='%d/%m/%Y %H:%M:%S', errors='coerce')
        
        if pd.isna(created_at):
            # Se created_at não puder ser convertido, pular o ticket
            continue
        
        if pd.notna(published_at):
            # Se published_at for válido, calcular a duração
            duracao_horas = (published_at - created_at).total_seconds() / 3600  # Convertendo para horas
            data_termino = published_at.strftime('%d de %b. de %Y')
        else:
            # Se published_at for inválido ou N/A
            duracao_horas = '-'
            data_termino = '-'
        
        # Pegando o status (etapa agrupada)
        status = ticket['status']
        
        # Adicionar dados à tabela
        tabela_dados.append({
            'Data Envio': created_at,
            'Etapa agrupada': status,
            'Duração em Horas': round(duracao_horas, 1) if isinstance(duracao_horas, (float, int)) else '-',
            'Data término': data_termino
        })

    # Converter para DataFrame
    df_tabela = pd.DataFrame(tabela_dados)

    # Verificar se o DataFrame não está vazio antes de exibir
    if not df_tabela.empty:
        # Ordenar pela coluna 'Data Envio' do mais recente para o menos recente
        df_tabela = df_tabela.sort_values(by='Data Envio', ascending=False)
        
        # Formatando 'Data Envio' para string novamente para exibição
        df_tabela['Data Envio'] = df_tabela['Data Envio'].dt.strftime('%d de %b. de %Y')
        
        # Exibir o DataFrame com a primeira coluna como índice
        st.dataframe(df_tabela.set_index('Data Envio'), use_container_width=True)
    else:
        st.write("Nenhuma solicitação de exclusão encontrada.")

def tendenciaAtendimentos(data_inicio, data_fim, dados_filtrados):
    # Gráfico de Linha de Tendência de Atendimentos por Dia
    st.markdown("<h4 style='text-align: center;'>Linha de Tendência de Atendimentos por Dia</h4>", unsafe_allow_html=True)

    # Definir a variável today (data atual)
    today = pd.to_datetime(datetime.now()).tz_localize('America/Sao_Paulo').date()  # Data atual como tz-aware

    # Extrair as datas de atendimento dos dados filtrados
    datas_atendimento = [dado["created_at"] for dado in dados_filtrados]
    df_atendimentos = pd.DataFrame(datas_atendimento, columns=["Data de Atendimento"])

    # Converter a coluna de data para datetime no formato correto
    df_atendimentos['Data de Atendimento'] = pd.to_datetime(df_atendimentos['Data de Atendimento'], format='%d/%m/%Y %H:%M:%S')

    # Contar atendimentos por dia
    contagem_atendimentos_por_dia = df_atendimentos['Data de Atendimento'].dt.date.value_counts().sort_index()

    # Converter as datas de início e fim para timestamps com fuso horário
    data_inicio_ts = pd.Timestamp(data_inicio).tz_localize('America/Sao_Paulo')
    data_fim_ts = pd.Timestamp(data_fim).tz_localize('America/Sao_Paulo')

    if not contagem_atendimentos_por_dia.empty:
        # Criar um DataFrame com a contagem dos atendimentos por dia
        df_contagem_dia = contagem_atendimentos_por_dia.reset_index()
        df_contagem_dia.columns = ['Data', 'Quantidade']

        # Converter a coluna 'Data' para datetime com fuso horário
        df_contagem_dia['Data'] = pd.to_datetime(df_contagem_dia['Data']).dt.tz_localize('America/Sao_Paulo')

        # Definir o índice como 'Data'
        df_contagem_dia.set_index('Data', inplace=True)

        # Adicionar o dia atual ao intervalo, se ainda não existir
        if today not in df_contagem_dia.index.date:  # Compare apenas a parte da data
            df_contagem_dia.loc[pd.Timestamp(today).tz_localize('America/Sao_Paulo')] = 0  # Inicializa o valor como 0 se a data não existir

        # Criar uma sequência de datas que cobre o intervalo completo
        full_range = pd.date_range(start=df_contagem_dia.index.min(), end=df_contagem_dia.index.max())

        # Reindexar o dataframe para preencher as datas faltantes com zero
        df_contagem_dia = df_contagem_dia.reindex(full_range, fill_value=0)
        df_contagem_dia.index.name = 'Data'

        # Filtrar o DataFrame com o período selecionado
        df_contagem_dia_limited = df_contagem_dia.loc[data_inicio_ts:data_fim_ts].reset_index()

        # Criar o gráfico com Altair com padding extra no eixo X
        chart = alt.Chart(df_contagem_dia_limited).mark_line(point=True).encode(
            x=alt.X('Data:T', title='', axis=alt.Axis(format='%d-%m', ticks=True, grid=False), scale=alt.Scale(padding=20)),  # Adicionar padding no eixo X
            y=alt.Y('Quantidade:Q', title='', axis=alt.Axis(format='d'),scale=alt.Scale(padding=20)),  # Título do eixo Y removido e formato definido para inteiros
            tooltip=['Data:T', 'Quantidade:Q']
        ).properties(
            height=400   # Altura ajustada
        ).interactive()

        # Exibir o gráfico no Streamlit com largura total
        st.altair_chart(chart, use_container_width=True)

    else:
        st.write("Sem dados para exibir.")

