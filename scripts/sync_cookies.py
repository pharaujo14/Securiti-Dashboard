"""
Sincroniza os dados de consentimento de cookies: busca na API da Securiti,
salva em Parquet no Google Cloud Storage, e consolida métricas diárias no MongoDB.

Isto é a MESMA lógica que estava em pagina_atualizar_cookies.py (fetch_missing_data
/ fetch_cookie_data / calcular_metricas / processar_para_mongo), só que sem depender
de um admin clicar manualmente na aba "Upload Cookies" do Streamlit.
Roda via GitHub Actions (ver .github/workflows/sync-cookies.yml), uma vez por dia.

Uso local (para testar antes de subir):
    export MONGO_USER=...
    export MONGO_PASSWORD=...
    export GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type": "service_account", ...}'
    export SECURITI_X_TIDENT=...
    export PROPERTY_API_KEY=... PROPERTY_API_SECRET=... PROPERTY_ORG_ID=...
    export CARREFOUR_API_KEY=... CARREFOUR_API_SECRET=... CARREFOUR_ORG_ID=...
    export SAMS_API_KEY=...     SAMS_API_SECRET=...     SAMS_ORG_ID=...
    export CCI_API_KEY=...      CCI_API_SECRET=...      CCI_ORG_ID=...
    python scripts/sync_cookies.py
"""

import io
import json
import sys
from datetime import datetime, timedelta

import pandas as pd
import requests
from google.cloud import storage
from google.oauth2.service_account import Credentials

from common import get_env, conecta_banco, logger

GCS_BUCKET_NAME = "cookies-c4"
API_URL = "https://app.securiti.ai/reporting/v1/sources/query?ref=getCmpCookieConsentRecords"

# Verificação de SSL LIGADA por padrão — ver comentário equivalente em sync_dsar.py.
SSL_VERIFY = get_env("SECURITI_SSL_VERIFY", required=False, default="true").lower() != "false"


def _gcs_client():
    creds_json = get_env("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    try:
        info = json.loads(creds_json)
    except json.JSONDecodeError:
        logger.error("GOOGLE_APPLICATION_CREDENTIALS_JSON não é um JSON válido.")
        sys.exit(1)
    credentials = Credentials.from_service_account_info(info)
    return storage.Client(credentials=credentials)


def _organizations():
    return {
        "property": {
            "x-api-key": get_env("PROPERTY_API_KEY"),
            "x-api-secret": get_env("PROPERTY_API_SECRET"),
            "x-org-id": get_env("PROPERTY_ORG_ID"),
        },
        "carrefour": {
            "x-api-key": get_env("CARREFOUR_API_KEY"),
            "x-api-secret": get_env("CARREFOUR_API_SECRET"),
            "x-org-id": get_env("CARREFOUR_ORG_ID"),
        },
        "sams": {
            "x-api-key": get_env("SAMS_API_KEY"),
            "x-api-secret": get_env("SAMS_API_SECRET"),
            "x-org-id": get_env("SAMS_ORG_ID"),
        },
        "cci": {
            "x-api-key": get_env("CCI_API_KEY"),
            "x-api-secret": get_env("CCI_API_SECRET"),
            "x-org-id": get_env("CCI_ORG_ID"),
        },
    }


def list_blobs(client, bucket_name):
    return [blob.name for blob in client.list_blobs(bucket_name)]


def upload_parquet_gcs(client, df, filename):
    output = io.BytesIO()
    df.to_parquet(output, engine="pyarrow")
    output.seek(0)
    blob = client.bucket(GCS_BUCKET_NAME).blob(filename)
    blob.upload_from_file(output, content_type="application/octet-stream")
    logger.info("Arquivo %s enviado para o GCS.", filename)


def fetch_cookie_data(start_date, end_date, x_tident, organizations):
    all_data = []
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())

    for org_name, credentials in organizations.items():
        offset = 0
        batch_size = 100000
        while True:
            headers = {
                "x-tident": x_tident,
                "x-api-key": credentials["x-api-key"],
                "x-api-secret": credentials["x-api-secret"],
                "x-org-id": credentials["x-org-id"],
            }
            payload = {
                "source": "category_consents_flat",
                "response_config": {"format": 1},
                "pagination": {"type": "limit-offset", "offset": offset, "limit": batch_size, "omit_total": True},
                "fields": [
                    {"name": "consent_id"}, {"name": "implicit_consent"}, {"name": "user_uuid"},
                    {"name": "consent_scanned_props_name"}, {"name": "consented_item_activity_id"},
                    {"name": "activity_timestamp"}, {"name": "consent_scanned_props_category"},
                    {"name": "domain_url"}, {"name": "consent_policy_id"}, {"name": "consent_domain"},
                    {"name": "consent_ip_address"}, {"name": "gpc_signal"}, {"name": "consent_geo_location_country"},
                ],
                "order_by": ["-activity_timestamp"],
                "skip_cache": True,
                "filter": {
                    "op": "and",
                    "value": [
                        {"op": "gte", "field": "activity_timestamp", "value": start_ts},
                        {"op": "lt", "field": "activity_timestamp", "value": end_ts},
                    ],
                },
            }

            try:
                response = requests.post(API_URL, json=payload, headers=headers, verify=SSL_VERIFY, timeout=120)
                response.raise_for_status()
            except requests.exceptions.RequestException as exc:
                logger.error("Erro ao buscar cookies de %s (offset %d): %s", org_name, offset, exc)
                break

            records = response.json().get("data", [])
            if not records:
                break

            for record in records:
                record["organization"] = org_name
            all_data.extend(records)
            logger.info("%s: %d registros recebidos (offset %d)", org_name, len(records), offset)
            offset += batch_size

    return pd.DataFrame(all_data)


def fetch_missing_data(gcs_client, x_tident, organizations):
    """Verifica e busca dados ausentes desde 01/06/24 até ontem."""
    start_date = datetime(2024, 6, 1)
    end_date = datetime.now() - timedelta(days=1)
    existing_blobs = set(list_blobs(gcs_client, GCS_BUCKET_NAME))

    while start_date <= end_date:
        filename = f"cookies_{start_date.strftime('%Y-%m-%d')}.parquet"
        if filename in existing_blobs:
            start_date += timedelta(days=1)
            continue

        logger.info("Buscando dados de cookies para %s...", start_date.strftime("%Y-%m-%d"))
        df = fetch_cookie_data(start_date, start_date + timedelta(days=1), x_tident, organizations)
        if not df.empty:
            upload_parquet_gcs(gcs_client, df, filename)
        else:
            logger.info("Nenhum dado encontrado para %s.", start_date.strftime("%Y-%m-%d"))
        start_date += timedelta(days=1)


def calcular_metricas(df, data_ref):
    resultados = []
    for org in df["organization"].unique():
        subset = df[df["organization"] == org].copy()

        if "consent_scanned_props_name" not in subset.columns or "consented_item_activity_id" not in subset.columns:
            logger.warning("Campos necessários ausentes para org %s", org)
            continue

        subset["consented_item_activity_id"] = pd.to_numeric(subset["consented_item_activity_id"], errors="coerce")
        subset["consent_scanned_props_name"] = subset["consent_scanned_props_name"].astype(str)
        subset = subset.dropna(subset=["consent_scanned_props_name", "consented_item_activity_id"])

        if subset.empty:
            items_by_category_id = {}
        else:
            agrupado = (
                subset.groupby(["consent_scanned_props_name", "consented_item_activity_id"])
                .size()
                .reset_index(name="count")
            )
            items_by_category_id = {
                f"{row['consent_scanned_props_name']} -- {int(row['consented_item_activity_id'])}": int(row["count"])
                for _, row in agrupado.iterrows()
            }

        # Cruzamento REAL domínio x categoria (quantos consents da categoria X
        # vieram do domínio Y). Antes, o gráfico "Categorias de Cookies por
        # Domínios" tentava reconstruir isso combinando `domains` e `categories`
        # (que são dois agregados independentes do dia inteiro) — o resultado
        # era todo domínio do dia recebendo o mesmo valor de cada categoria,
        # o que "espelhava" domínios da mesma organização. Guardamos como
        # lista de registros (não como dict aninhado por domínio) porque
        # domínio contém ponto (ex.: "carrefour.com.br"), e chave de campo
        # com ponto no Mongo é melhor evitar.
        if subset.empty or "domain_url" not in subset.columns or "consent_scanned_props_category" not in subset.columns:
            domain_categories = []
        else:
            agrupado_dom_cat = (
                subset.groupby(["domain_url", "consent_scanned_props_category"])
                .size()
                .reset_index(name="count")
            )
            domain_categories = [
                {
                    "domain": row["domain_url"],
                    "categoria": row["consent_scanned_props_category"],
                    "valor": int(row["count"]),
                }
                for _, row in agrupado_dom_cat.iterrows()
            ]

        resultados.append({
            "date": data_ref.strftime("%Y-%m-%d"),
            "organization": org,
            "metrics": {
                "total_consents": subset["consent_id"].nunique(),
                "unique_users": subset["user_uuid"].nunique(),
                "implicit_ratio": float((subset["implicit_consent"] == True).sum() / len(subset)) if len(subset) > 0 else 0.0,
                "gpc_enabled": int((subset["gpc_signal"] == True).sum()),
                "categories": subset["consent_scanned_props_category"].value_counts().to_dict(),
                "countries": subset["consent_geo_location_country"].value_counts().to_dict(),
                "domains": subset["domain_url"].value_counts().to_dict(),
                "items_by_category_id": items_by_category_id,
                "domain_categories": domain_categories,
            },
        })
    return resultados


def processar_para_mongo(collection, gcs_client):
    # collection['consolidado_cookies'] vira, no pymongo, a collection pontuada
    # "dashboard_blackfriday.consolidado_cookies" — é exatamente o mesmo lugar
    # que pagina_cookies.py já lê hoje (ver nota em common.conecta_banco()).
    consolidado_collection = collection["consolidado_cookies"]
    start_date = datetime(2024, 3, 1)
    end_date = datetime.now() - timedelta(days=1)
    existing_blobs = set(list_blobs(gcs_client, GCS_BUCKET_NAME))

    inseridos = 0
    while start_date <= end_date:
        filename = f"cookies_{start_date.strftime('%Y-%m-%d')}.parquet"
        data_str = start_date.strftime("%Y-%m-%d")

        if filename in existing_blobs and not consolidado_collection.find_one({"date": data_str}):
            blob = gcs_client.bucket(GCS_BUCKET_NAME).blob(filename)
            buffer = io.BytesIO()
            blob.download_to_file(buffer)
            buffer.seek(0)
            df = pd.read_parquet(buffer)
            metricas = calcular_metricas(df, start_date)
            if metricas:
                consolidado_collection.insert_many(metricas)
                inseridos += len(metricas)
                logger.info("Consolidado de %s inserido no MongoDB.", data_str)

        start_date += timedelta(days=1)

    logger.info("Total de documentos consolidados inseridos: %d", inseridos)


def main():
    collection = conecta_banco()
    gcs_client = _gcs_client()
    x_tident = get_env("SECURITI_X_TIDENT")
    organizations = _organizations()

    fetch_missing_data(gcs_client, x_tident, organizations)
    processar_para_mongo(collection, gcs_client)
    logger.info("Sincronização de Cookies concluída com sucesso.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Sincronização de Cookies falhou")
        sys.exit(1)
