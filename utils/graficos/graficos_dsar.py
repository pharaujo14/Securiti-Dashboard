import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import altair as alt

from io import BytesIO
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
    
    # Contagem dos tipos de solicitação com base no type_tags
    tipos_solicitacao = [traducoes[dado["type_tags"]] for dado in dados_filtrados if dado["type_tags"] in traducoes]
    df_tipos_solicitacao = pd.DataFrame(tipos_solicitacao, columns=["Tipo de Solicitação"])
    contagem_tipos = df_tipos_solicitacao["Tipo de Solicitação"].value_counts()

    if not contagem_tipos.empty:
        # Cria o DataFrame para o Seaborn
        df_contagem_tipos = contagem_tipos.reset_index()
        df_contagem_tipos.columns = ['Tipo de Solicitação', 'Quantidade']

        # Cria o gráfico de barras
        plt.figure(figsize=(10, 6))
        sns.barplot(x='Quantidade', y='Tipo de Solicitação', data=df_contagem_tipos, color='#0000CD')

        # Adiciona os valores fora das barras
        for i, v in enumerate(df_contagem_tipos['Quantidade']):
            plt.text(v + 1, i, f'{v}', color='black', va='center', fontweight='bold')

        # Ajustes de limites e remoção de rótulos
        plt.xlim(0, df_contagem_tipos['Quantidade'].max() + 5)
        plt.xlabel('')
        plt.ylabel('')

        sns.despine()
        plt.grid(False)

        # Salva o gráfico como uma imagem em um buffer BytesIO
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()  # Fecha o gráfico para liberar memória

        return img_buffer  # Retorna o buffer da imagem
    else:
        return None  # Retorna None se não houver dados

def contagemStatus(dados_filtrados):

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

        # Salvar o gráfico em um buffer de imagem
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        plt.close()  # Fecha o plot para liberar memória
        img_buffer.seek(0)  # Define o início do buffer
        return img_buffer
    else:
        return None

def atendimentosDia(dados_filtrados):

    # Extrair datas de atendimento
    datas_atendimento = [dado["created_at"] for dado in dados_filtrados]
    df_atendimentos = pd.DataFrame(datas_atendimento, columns=["Data de Atendimento"])

    # Tentar converter os dados
    try:
        df_atendimentos['Data de Atendimento'] = pd.to_datetime(df_atendimentos['Data de Atendimento'], unit='ms')
    except ValueError:
        df_atendimentos['Data de Atendimento'] = pd.to_datetime(df_atendimentos['Data de Atendimento'], format='%d/%m/%Y %H:%M:%S')

    # Contar atendimentos por dia
    contagem_atendimentos_por_dia = df_atendimentos['Data de Atendimento'].dt.date.value_counts().sort_index()

    if not contagem_atendimentos_por_dia.empty:
        df_contagem_dia = contagem_atendimentos_por_dia.reset_index()
        df_contagem_dia.columns = ['Data', 'Quantidade']

        # Criar uma sequência de datas
        full_range = pd.date_range(start=df_atendimentos['Data de Atendimento'].min().date(),
                                   end=df_atendimentos['Data de Atendimento'].max().date(), freq='D')

        # Reindexar para preencher dias ausentes com zero
        df_contagem_dia = df_contagem_dia.set_index('Data').reindex(full_range, fill_value=0).reset_index()
        df_contagem_dia.columns = ['Data', 'Quantidade']

        # Selecionar os últimos 30 dias
        df_contagem_dia = df_contagem_dia.tail(30)
        df_contagem_dia['Data'] = df_contagem_dia['Data'].dt.strftime('%d-%m')

        # Criar o gráfico em uma figura grande
        fig, ax = plt.subplots(figsize=(18, 9))  # Aumentar tamanho da figura
        sns.barplot(x='Data', y='Quantidade', data=df_contagem_dia, color='#0000CD', ax=ax)

        for i, v in enumerate(df_contagem_dia['Quantidade']):
            ax.text(i, v + 0.5, f'{v}', color='black', ha='center', fontweight='bold')

        plt.xticks(rotation=45)
        ax.set_ylabel('')
        ax.set_xlabel('')
        sns.despine()
        plt.grid(False)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        # Salvar o gráfico em alta resolução no buffer
        img_buffer = BytesIO()
        fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=200)  # Aumentar DPI para melhor qualidade
        plt.close(fig)
        img_buffer.seek(0)
        return img_buffer
    else:
        return None

def solicitacoesExclusao(dados_filtrados):

    # Filtrar apenas os tickets de exclusão ('type_tags': 'erasure')
    tickets_exclusao = [ticket for ticket in dados_filtrados]

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
            data_termino = published_at
        else:
            # Se published_at for inválido ou N/A
            duracao_horas = '-'
            data_termino = '-'
        
        # Pegando o status (etapa agrupada)
        status = ticket['status']
        
        # Adicionar dados à tabela
        tabela_dados.append({
            'ID': str(ticket['id']),
            'Tipo': traducoes.get(ticket["type_tags"], "-"),  # Adicionando o valor traduzido diretamente
            'Detalhes da Requisição': ticket['detalhes_req'] if ticket['detalhes_req'] else '-',
            'Data Envio': created_at,
            'Etapa agrupada': status if status else '-',
            'Duração H': round(duracao_horas, 1) if isinstance(duracao_horas, (float, int)) else '-',
            'Data término': data_termino
        })

    # Converter para DataFrame
    df_tabela = pd.DataFrame(tabela_dados)

    # Verificar se o DataFrame não está vazio antes de exibir
    if not df_tabela.empty:

        # Ordenar pela coluna 'Data Envio' do mais recente para o menos recente
        df_tabela = df_tabela.sort_values(by='Data Envio', ascending=False)

        # Reordenar as colunas para que 'ID' seja a primeira
        df_tabela = df_tabela[['ID', 'Tipo', 'Detalhes da Requisição', 'Data Envio', 'Etapa agrupada', 'Duração H', 'Data término']]
        
        # Garantir que 'Data Envio' tenha valores datetime válidos antes de usar o .dt.strftime
        df_tabela['Data Envio'] = pd.to_datetime(df_tabela['Data Envio'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
        df_tabela['Data Envio'] = df_tabela['Data Envio'].fillna('-')

        # Garantir que 'Data término' tenha valores datetime válidos antes de usar o .dt.strftime
        df_tabela['Data término'] = pd.to_datetime(df_tabela['Data término'], errors='coerce')
        df_tabela['Data término'] = df_tabela['Data término'].apply(
            lambda x: x.strftime('%d/%m/%Y %H:%M') if pd.notna(x) else '-'
        )

        return df_tabela
    else:
        return pd.DataFrame()


def tendenciaAtendimentos(data_inicio, data_fim, dados_filtrados):
    # Definir a variável today (data atual)
    today = pd.to_datetime(datetime.now()).tz_localize('America/Sao_Paulo').date()

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
        if today not in df_contagem_dia.index.date:
            df_contagem_dia.loc[pd.Timestamp(today).tz_localize('America/Sao_Paulo')] = 0

        # Criar uma sequência de datas que cobre o intervalo completo
        full_range = pd.date_range(start=df_contagem_dia.index.min(), end=df_contagem_dia.index.max())

        # Reindexar o dataframe para preencher as datas faltantes com zero
        df_contagem_dia = df_contagem_dia.reindex(full_range, fill_value=0)
        df_contagem_dia.index.name = 'Data'

        # Filtrar o DataFrame com o período selecionado
        df_contagem_dia_limited = df_contagem_dia.loc[data_inicio_ts:data_fim_ts].reset_index()

        # Plotar o gráfico com matplotlib
        plt.figure(figsize=(12, 6))  # Tamanho ajustado para ocupar a largura total
        plt.plot(
            df_contagem_dia_limited['Data'].to_numpy(),
            df_contagem_dia_limited['Quantidade'].to_numpy(),
            marker='.',
            linestyle='-',
            color='b'
        )

        # Ajuste do formato de data para DD-MM
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d-%m'))

        # Remover grades internas
        plt.grid(visible=False)

        # Remover título e labels dos eixos
        plt.xlabel('')
        plt.ylabel('')

        # Ajuste da rotação dos rótulos do eixo x
        plt.xticks(rotation=45)

        # Salvar o gráfico no buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')  # Ajuste para ocupar o espaço completo
        buf.seek(0)  # Voltar ao início do buffer para leitura

        # Retornar o buffer para ser utilizado em outras funções, como geração de PDF
        return buf

    else:
        st.write("Sem dados para exibir.")
        return None
