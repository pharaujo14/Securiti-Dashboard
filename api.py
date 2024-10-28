import requests
import json
from datetime import datetime
import streamlit as st

# Função para ajustar o status
def ajustar_status(status_code):
    status_dict = {
        1: "Aberto",
        2: "Em andamento",
        3: "Concluído",
        4: "Negado"
    }
    return status_dict.get(status_code, "Desconhecido")

# Função para converter timestamps para o formato brasileiro
def converter_data(timestamp):
    if timestamp and timestamp > 0:
        return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M:%S')
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
        "x-tident":"e90cbf5f-2197-4288-b3ed-a2bee3367563",
        "x-api-key":"Z8uvzGFFZ44me8mbVoWatKFv244MzP6WXFTF4VQ4",
        "x-api-secret":"qh6GY6lqatbAydzpb4UNAtq52zSz4jjytg6zW616",
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
            "organizacao": ticket_data.get("custom_fields", {}).get("organizacao")
        }
        
        return extracted_data

    except requests.exceptions.RequestException as e:
        print("Erro ao fazer a requisição:", e)
        return None

def atualizar_dados(collection, progresso):
    dados_api = buscar_dados_api()
    dados_mongo = buscar_dados(collection)

    add_mongo = calcula_diferenca(dados_api, dados_mongo)

    total_dados = len(add_mongo)  # Total de dados a serem processados

    for index, id in enumerate(add_mongo):
        dado = get_ticket_data(id)

        # Seleciona apenas os campos necessários
        dado_filtrado = {
            "org_unit_name": dado.get("org_unit_name"),
            "type_tags": dado.get("type_tags"),
            "status": ajustar_status(dado.get("status")),
            "published_at": dado.get("published_at"),
            "created_at": dado.get("created_at"),
            "id": dado.get("id"),
            "organizacao": dado.get("organizacao")
        }

        # Insere no MongoDB somente se o ID ainda não existe
        if not collection.find_one({"id": dado_filtrado["id"]}):  
            collection.insert_one(dado_filtrado)

        # Atualiza a barra de progresso
        percent = (index + 1) / total_dados
        progresso.progress(percent)  # Atualiza o progresso no Streamlit

    print("Dados atualizados com sucesso no MongoDB.")

def buscar_dados(collection):
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