"""
Sincroniza os tickets de DSAR da API da Securiti para o MongoDB.

Isto é a MESMA lógica que estava em utils/api.py (atualizar_dados / buscar_dados_api
/ get_ticket_data), só que sem depender do Streamlit estar com uma aba aberta.
Roda via GitHub Actions (ver .github/workflows/sync-dsar.yml), de hora em hora.

Uso local (para testar antes de subir):
    export MONGO_USER=...
    export MONGO_PASSWORD=...
    export SECURITI_X_TIDENT=...
    export SECURITI_DEFAULT_API_KEY=...
    export SECURITI_DEFAULT_API_SECRET=...
    python scripts/sync_dsar.py
"""

import json
import sys
from datetime import datetime

import pytz
import requests

from common import get_env, conecta_banco, logger

API_TICKETS_URL = "https://app.securiti.ai/reporting/v1/sources/query?ref=getListOfTickets"
API_TICKET_DETAIL_URL = "https://app.securiti.ai/privaci/v1/admin/dsr/tickets/{ticket_id}"

# Verificação de SSL LIGADA por padrão (o código original desligava com verify=False,
# o que é um risco de segurança). Se a API da Securiti exigir um certificado
# corporativo específico e isso quebrar, defina SECURITI_SSL_VERIFY=false
# como último recurso, mas o ideal é resolver o certificado.
SSL_VERIFY = get_env("SECURITI_SSL_VERIFY", required=False, default="true").lower() != "false"

STATUS_MAP = {1: "Em andamento", 2: "Em andamento", 3: "Concluído", 4: "Negado"}


def ajustar_status(status_code):
    return STATUS_MAP.get(status_code, "Desconhecido")


def converter_data(timestamp):
    if timestamp and timestamp > 0:
        tz_brasil = pytz.timezone("America/Sao_Paulo")
        dt_utc = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
        return dt_utc.astimezone(tz_brasil).strftime("%d/%m/%Y %H:%M:%S")
    return "N/A"


def _headers():
    return {
        "x-tident": get_env("SECURITI_X_TIDENT"),
        "x-api-key": get_env("SECURITI_DEFAULT_API_KEY"),
        "x-api-secret": get_env("SECURITI_DEFAULT_API_SECRET"),
        "accept": "application/json",
        "Content-Type": "application/json",
    }


def buscar_dados_api():
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
            {"name": "org_unit_name"},
        ],
        "pagination": {"type": "limit-offset", "offset": 0, "limit": 2500, "omit_total": True},
        "order_by": ["-id"],
    }

    try:
        response = requests.post(
            API_TICKETS_URL, headers=_headers(), data=json.dumps(payload),
            verify=SSL_VERIFY, timeout=60,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.error("Falha ao buscar tickets na API da Securiti: %s", exc)
        # Propaga o erro em vez de engolir e devolver [] silenciosamente
        # (era exatamente esse silêncio que escondia a falha por dias).
        raise

    result = response.json()
    dados_extraidos = []
    for item in result.get("data", []):
        dados_extraidos.append({
            "org_unit_name": item.get("org_unit_name"),
            "type_tags": item.get("type_tags"),
            "status": ajustar_status(item.get("status")),
            "published_at": converter_data(item.get("published_at") / 1000) if item.get("published_at") else "N/A",
            "created_at": converter_data(item.get("created_at") / 1000) if item.get("created_at") else "N/A",
            "id": item.get("id"),
        })
    return dados_extraidos


def get_ticket_data(ticket_id):
    url = API_TICKET_DETAIL_URL.format(ticket_id=ticket_id)
    try:
        response = requests.get(url, headers=_headers(), verify=SSL_VERIFY, timeout=30)
        response.raise_for_status()
        data = response.json()
        ticket_data = data.get("data", [{}])[0]
    except requests.exceptions.RequestException as exc:
        logger.warning("Erro ao buscar detalhes do ticket %s: %s", ticket_id, exc)
        return None

    return {
        "org_unit_name": ticket_data.get("org_unit_name"),
        "type_tags": ticket_data.get("type_tags"),
        "status": ticket_data.get("status"),
        "published_at": converter_data(ticket_data.get("published_at") / 1000) if ticket_data.get("published_at") else "N/A",
        "created_at": converter_data(ticket_data.get("created_at") / 1000) if ticket_data.get("created_at") else "N/A",
        "id": ticket_data.get("id"),
        "organizacao": ticket_data.get("custom_fields", {}).get("organizacao"),
        "detalhes_req": ticket_data.get("custom_fields", {}).get("requestDetails"),
    }


def calcula_diferenca(dados_api, dados_mongo):
    ids_api = {d["id"] for d in dados_api}
    ids_mongo = {d["id"] for d in dados_mongo}
    return list(ids_api - ids_mongo)


def calcula_diferenca_status(dados_api, dados_mongo):
    status_mongo = {d["id"]: d["status"] for d in dados_mongo}
    return [d["id"] for d in dados_api if d["id"] in status_mongo and d["status"] != status_mongo[d["id"]]]


def registrar_atualizacao(collection_historico):
    tz_brasil = pytz.timezone("America/Sao_Paulo")
    agora_brasil = datetime.now(tz_brasil)
    collection_historico.insert_one({"data_hora": agora_brasil.astimezone(pytz.utc)})


def main():
    collection = conecta_banco()
    # Atenção: isto NÃO é uma coleção "historico_atualizacoes" separada — o pymongo
    # trata collection['x'] como uma sub-coleção com nome pontuado
    # "dashboard_blackfriday.historico_atualizacoes". É assim que o app.py original
    # já lia/gravava o histórico, então mantemos exatamente o mesmo caminho aqui
    # para não duplicar/perder o histórico de atualizações.
    collection_historico = collection["historico_atualizacoes"]

    try:
        collection.create_index("id", unique=True)
    except Exception:
        pass

    dados_api = buscar_dados_api()
    dados_mongo = list(collection.find())

    logger.info("Tickets retornados pela API: %d", len(dados_api))
    logger.info("Tickets já existentes no Mongo: %d", len(dados_mongo))

    if not dados_api:
        logger.warning("A API não retornou nenhum ticket. Encerrando sem alterar o Mongo.")
        # Não grava "atualização" no histórico se a API não respondeu nada —
        # assim o "Última atualização" do dashboard reflete a última sincronização
        # que teve dados de verdade, e não mascara uma falha da API.
        sys.exit(1)

    # 1) Atualiza status de tickets que mudaram
    ids_status_alterados = calcula_diferenca_status(dados_api, dados_mongo)
    for ticket_id in ids_status_alterados:
        dado = get_ticket_data(ticket_id)
        if not dado:
            logger.warning("Dado não encontrado para o ticket %s ao atualizar status", ticket_id)
            continue
        collection.update_one(
            {"id": ticket_id},
            {"$set": {"status": ajustar_status(dado.get("status")), "published_at": dado.get("published_at")}},
        )
    logger.info("Tickets com status atualizado: %d", len(ids_status_alterados))

    # 2) Insere tickets novos
    ids_novos = calcula_diferenca(dados_api, dados_mongo)
    inseridos = 0
    for ticket_id in ids_novos:
        dado = get_ticket_data(ticket_id)
        if not dado:
            logger.warning("Dado ausente ao tentar adicionar o ticket %s", ticket_id)
            continue

        dado_filtrado = {
            "org_unit_name": dado.get("org_unit_name"),
            "type_tags": dado.get("type_tags"),
            "status": ajustar_status(dado.get("status")),
            "published_at": dado.get("published_at"),
            "created_at": dado.get("created_at"),
            "id": dado.get("id"),
            "organizacao": dado.get("organizacao"),
            "detalhes_req": dado.get("detalhes_req"),
        }
        if not collection.find_one({"id": dado_filtrado["id"]}):
            collection.insert_one(dado_filtrado)
            inseridos += 1

    logger.info("Tickets novos inseridos: %d", inseridos)

    registrar_atualizacao(collection_historico)
    logger.info("Sincronização de DSAR concluída com sucesso.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Sincronização de DSAR falhou")
        sys.exit(1)
