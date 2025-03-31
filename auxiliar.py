import pytz
import pandas as pd

from datetime import datetime
from aux_cookies import fetch_missing_data, processar_para_mongo

# Buscar a última atualização
def obter_ultima_atualizacao(collection_historico):
    
    fuso_horario_brasilia = pytz.timezone("America/Sao_Paulo")
    ultimo_registro = collection_historico.find_one(sort=[("data_hora", -1)])
    if ultimo_registro and isinstance(ultimo_registro["data_hora"], datetime):
        # Garante que o datetime está em UTC e converte para o fuso de Brasília
        data_utc = ultimo_registro["data_hora"].replace(tzinfo=pytz.utc)
        data_brasilia = data_utc.astimezone(fuso_horario_brasilia)
        return data_brasilia.strftime('%d/%m/%Y %H:%M:%S')
    return "Nunca atualizado"

# Função para filtrar dados por organização e período
def filtrar_dados(dados, org_selecionada, data_inicio, data_fim):
    # Converter data para datetime com hora 00:00:00
    data_inicio_ts = int(datetime.combine(data_inicio, datetime.min.time()).timestamp())
    data_fim_ts = int(datetime.combine(data_fim, datetime.max.time()).timestamp())
    
    # Filtrar os dados com base na organização e no período
    dados_filtrados = [
        dado for dado in dados
        if (org_selecionada == 'Todas' or dado["organizacao"] == org_selecionada) and
           data_inicio_ts <= datetime.strptime(dado["created_at"], '%d/%m/%Y %H:%M:%S').timestamp() <= data_fim_ts
    ]
    return dados_filtrados

def calcular_tempo_medio(dados):
    if len(dados) == 0:
        return 0

    # Converter para DataFrame
    if isinstance(dados, list):
        dados = pd.DataFrame(dados)
    
    # Renomear as colunas para mais clareza (opcional)
    DATA_INICIO = 'created_at'
    DATA_FIM = 'published_at'

    # Converter colunas de data para datetime
    dados[DATA_INICIO] = pd.to_datetime(dados[DATA_INICIO], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    dados[DATA_FIM] = pd.to_datetime(dados[DATA_FIM], format='%d/%m/%Y %H:%M:%S', errors='coerce')

    # Separar atendimentos finalizados e em andamento
    finalizados = dados[dados[DATA_FIM].notna()]
    em_andamento = dados[dados[DATA_FIM].isna()]

    # Calcular o tempo em dias para os finalizados
    finalizados['tempo_atendimento'] = (finalizados[DATA_FIM] - finalizados[DATA_INICIO]).dt.total_seconds() / 86400

    # Calcular o tempo em dias para os em andamento (usando a data atual como referência)
    em_andamento['tempo_atendimento'] = (pd.Timestamp.now() - em_andamento[DATA_INICIO]).dt.total_seconds() / 86400

    # Concatenar os dois DataFrames
    todos_dados = pd.concat([finalizados, em_andamento])

    # Calcular a média dos tempos de atendimento
    tempo_medio = todos_dados['tempo_atendimento'].mean()
    
    return round(tempo_medio, 2) if not pd.isna(tempo_medio) else 0

def atualizacao_periodica():
    agora = datetime.now()

    # Se for 04:00 da manhã, executa as funções
    if agora.hour == 4 and agora.minute == 0:
        fetch_missing_data()
        processar_para_mongo()