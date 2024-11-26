import requests
import json
import streamlit as st
import pytz

from datetime import datetime, timedelta

# Função para ajustar o status
def ajustar_status(status_code):
    status_dict = {
        1: "Em andamento",
        2: "Em andamento",
        3: "Concluído",
        4: "Negado"
    }
    return status_dict.get(status_code, "Desconhecido")

def converter_data(timestamp):
    if timestamp and timestamp > 0:
        # Definindo o timezone brasileiro (BRT ou America/Sao_Paulo)
        timezone_brasil = pytz.timezone("America/Sao_Paulo")
        # Convertendo o timestamp para datetime no fuso horário UTC
        datetime_utc = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
        # Ajustando para o horário do Brasil
        datetime_brasil = datetime_utc.astimezone(timezone_brasil)
        # Formatando no padrão desejado
        return datetime_brasil.strftime('%d/%m/%Y %H:%M:%S')
    return "N/A"  # Se for 0 ou None, retorna "N/A"

def buscar_dados_api():
    url = "https://app.securiti.ai/reporting/v1/sources/query?ref=getListOfTickets"
    headers = {
        "x-tident": st.secrets["api"]["x_tident"],
        "x-api-key": st.secrets["api"]["x_api_key"],
        "x-api-secret": st.secrets["api"]["x_api_secret"],
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "source": "dsr_ticket",
        "response_config": {"format": 1},
        "skip_cache": True,
        "fields": [
            {"name": "id"},
            {"name": "status"},
            {"name": "type_tags"},
            {"name": "created_at"},
            {"name": "published_at"},
            {"name": "org_unit_name"}
        ],
        "pagination": {"type": "limit-offset", "offset": 0, "limit": 2500, "omit_total": True},
        "order_by": ["-id"]
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)

    if response.status_code == 200:
        result = response.json()
        dados_extraidos = []

        # Extrair os campos específicos
        for item in result.get("data", []):
            dado = {
                "org_unit_name": item.get("org_unit_name"),
                "type_tags": item.get("type_tags"),
                "status": ajustar_status(item.get("status")),
                "published_at": converter_data(item.get("published_at") / 1000) if item.get("published_at") else "N/A",
                "created_at": converter_data(item.get("created_at") / 1000) if item.get("created_at") else "N/A",
                "id": item.get("id")
            }
            dados_extraidos.append(dado)

        return dados_extraidos

    else:
        print(f"Erro {response.status_code}: {response.text}")
        return []

def get_ticket_data(ticket_id):
    url = f"https://app.securiti.ai/privaci/v1/admin/dsr/tickets/{ticket_id}"
    headers = {
        "x-tident": st.secrets["api"]["x_tident"],
        "x-api-key": st.secrets["api"]["x_api_key"],
        "x-api-secret": st.secrets["api"]["x_api_secret"],
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, verify=False)  # Ignora a verificação SSL
        response.raise_for_status()
        data = response.json()  # Converte a resposta para JSON

        # Extrair os campos desejados
        ticket_data = data.get("data", [{}])[0]
        
        # Extrair campos específicos
        extracted_data = {
            "org_unit_name": ticket_data.get("org_unit_name"),
            "type_tags": ticket_data.get("type_tags"),
            "status": ticket_data.get("status"),
            "published_at": converter_data(ticket_data.get("published_at") / 1000) if ticket_data.get("published_at") else "N/A",
            "created_at": converter_data(ticket_data.get("created_at") / 1000) if ticket_data.get("created_at") else "N/A",
            "id": ticket_data.get("id"),
            "organizacao": ticket_data.get("custom_fields", {}).get("organizacao"),
            "detalhes_req": ticket_data.get("custom_fields", {}).get("requestDetails")
        }
        
        return extracted_data

    except requests.exceptions.RequestException as e:
        print("Erro ao fazer a requisição:", e)
        return None

def atualizar_dados(collection, collection_historico):
    dados_api = buscar_dados_api()
    dados_mongo = buscar_dados(collection)

    # IDs com alteração no status
    ids_status_alterados = calcula_diferenca_status(dados_api, dados_mongo)
    
    # Atualiza o campo status e published_at para os IDs que mudaram
    for id_alterado in ids_status_alterados:
        dado = get_ticket_data(id_alterado)
        novo_status = ajustar_status(dado.get("status"))
        novo_published_at = dado.get("published_at")

        collection.update_one(
            {"id": id_alterado},
            {"$set": {"status": novo_status, "published_at": novo_published_at}}
        )

    # IDs que precisam ser adicionados ao MongoDB
    add_mongo = calcula_diferenca(dados_api, dados_mongo)

    total_dados = len(add_mongo)
    for index, id in enumerate(add_mongo):
        dado = get_ticket_data(id)
        dado_filtrado = {
            "org_unit_name": dado.get("org_unit_name"),
            "type_tags": dado.get("type_tags"),
            "status": ajustar_status(dado.get("status")),
            "published_at": dado.get("published_at"),
            "created_at": dado.get("created_at"),
            "id": dado.get("id"),
            "organizacao": dado.get("organizacao"),
            "detalhes_req": dado.get("detalhes_req")
        }

        if not collection.find_one({"id": dado_filtrado["id"]}):  
            collection.insert_one(dado_filtrado)

    # Registrar a atualização no histórico
    registrar_atualizacao(collection_historico)

    print("Dados atualizados com sucesso no MongoDB.")

def buscar_dados(collection):

    try:
        # Criar índice único no campo "id" para evitar duplicações
        collection.create_index("id", unique=True)
    except:
        print()

    try:
        # Recupera todos os documentos da coleção
        dados = list(collection.find())
        # Opcional: Imprime a quantidade de documentos recuperados
        print(f"{len(dados)} documentos encontrados.")
        return dados

    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return []

def calcula_diferenca(dados_api, dados_mongo):
    
    ids_api = set()

    for index, dado in enumerate(dados_api):
        ids_api.add(dado["id"])

    ids_mongo = set()
    for index, dado in enumerate(dados_mongo):
        ids_mongo.add(dado["id"])

    return list(ids_api.difference(ids_mongo))

def calcula_diferenca_status(dados_api, dados_mongo):
    # Cria um dicionário para os dados do MongoDB, mapeando IDs para o status
    status_mongo = {dado["id"]: dado["status"] for dado in dados_mongo}

    ids_status_alterados = []

    for dado in dados_api:
        id_atual = dado["id"]
        status_api = dado["status"]

        # Verifica se o ID existe em dados_mongo e se o status é diferente
        if id_atual in status_mongo and status_api != status_mongo[id_atual]:
            ids_status_alterados.append(id_atual)

    print(ids_status_alterados)
    return ids_status_alterados

def registrar_atualizacao(collection_historico):
    
    """Registra a data e hora da última atualização na coleção 'historico_atualizacoes' no horário UTC."""
    fuso_horario_brasilia = pytz.timezone("America/Sao_Paulo")
    data_atualizacao_brasilia = datetime.now(fuso_horario_brasilia)
    data_atualizacao_utc = data_atualizacao_brasilia.astimezone(pytz.utc)  # Converte para UTC

    data_atualizacao = {
        "data_hora": data_atualizacao_utc
    }
    collection_historico.insert_one(data_atualizacao)
