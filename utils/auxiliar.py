import psutil
import streamlit as st
import requests
import re
import random
import string
import pytz
import pandas as pd

from datetime import datetime
from pagina_atualizar_cookies import fetch_missing_data, processar_para_mongo

from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

# Função para verificar se o arquivo está em uso
def is_file_in_use(file_path):
    for proc in psutil.process_iter(['open_files']):
        try:
            for file in proc.info['open_files'] or []:
                if file.path == file_path:
                    return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return False

# Configuração da Conta de Serviço para o Google Drive
def upload_to_drive(file_name, file_path, folder_id, custom_name):
    try:
        # Carregar as credenciais do `secrets.toml`
        credentials = Credentials.from_service_account_info(
            st.secrets["google_drive"],
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        # Atualizar o token manualmente
        session = requests.Session()
        session.verify = False  # Ignorar verificação de certificado SSL
        request = Request(session=session)
        if not credentials.valid:
            credentials.refresh(request)

        # URL do Google Drive para upload
        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable"
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }

        # Configuração dos metadados do arquivo
        metadata = {
            "name": custom_name,
            "parents": [folder_id]
        }
        response = session.post(url, headers=headers, json=metadata)
        print(f"Response Status: {response.status_code}")
        print(f"Response Content: {response.content.decode()}")

        if response.status_code not in [200, 201]:
            st.error(f"Erro ao inicializar o upload: {response.content.decode()}")
            return None

        # URL de upload retornada pelo Google
        upload_url = response.headers["Location"]
        if not upload_url:
            print("Erro: URL de upload não encontrada no cabeçalho.")
            return

        # Upload do arquivo
        with open(file_path, "rb") as f:
            upload_response = session.put(upload_url, headers={"Content-Type": "application/octet-stream"}, data=f)
            print(f"Upload Response Status: {upload_response.status_code}")
            print(f"Upload Response Content: {upload_response.content.decode()}")

        if upload_response.status_code in [200, 201]:
            file_id = upload_response.json().get("id")
            return file_id
        else:
            st.error(f"Erro ao fazer upload do arquivo: {upload_response.content.decode()}")
            return None
    except Exception as e:
        st.error(f"Erro ao fazer upload para o Google Drive: {e}")
        return None
    
def validar_senha(senha):
    return (
        len(senha) >= 8 and
        any(c.isupper() for c in senha) and
        any(c.islower() for c in senha) and
        any(c.isdigit() for c in senha) and
        any(not c.isalnum() for c in senha)
    )

def gerar_senha_automatica():
    """
    Gera uma senha forte que inclui:
    - Pelo menos uma letra maiúscula
    - Pelo menos uma letra minúscula
    - Pelo menos um número
    - Pelo menos um caractere especial
    - Comprimento mínimo de 8 caracteres
    """
    caracteres = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    senha = [
        random.choice(string.ascii_uppercase),  # Garantir uma maiúscula
        random.choice(string.ascii_lowercase),  # Garantir uma minúscula
        random.choice(string.digits),           # Garantir um número
        random.choice("!@#$%^&*()-_=+"),        # Garantir um caractere especial
    ]
    senha += random.choices(caracteres, k=8 - len(senha))  # Restante aleatório
    random.shuffle(senha)  # Misturar os caracteres
    return ''.join(senha)

def validar_email(email):
    """
    Verifica se o e-mail é válido.
    """
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def formatar_nome(email):
    """
    Formata o nome a partir de um e-mail no formato 'nome.sobrenome@dominio.com'.
    """
    nome_sobrenome = email.split('@')[0]  # Pega a parte antes do @
    partes = nome_sobrenome.split('.')    # Divide em partes pelo '.'
    if len(partes) >= 2:
        nome = partes[0].capitalize()    # Capitaliza o primeiro nome
        sobrenome = partes[1].capitalize()  # Capitaliza o sobrenome
        return f"{nome} {sobrenome}"
    return nome_sobrenome.capitalize()  # Caso não tenha sobrenome, usa apenas o nome

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
