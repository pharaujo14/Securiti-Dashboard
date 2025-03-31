import streamlit as st
import requests
import pandas as pd
import urllib3
import io
import ssl

from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from google.cloud import storage
from conectaBanco import conectaBanco

# Ignorar verificação SSL globalmente
ssl._create_default_https_context = ssl._create_unverified_context

# Desativar avisos de requisição insegura
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Criar credenciais a partir do Streamlit secrets
credentials = Credentials.from_service_account_info(st.secrets["google_cloud"])

# Criar cliente de armazenamento
client = storage.Client(credentials=credentials)

# Configuração do Google Cloud Storage
GCS_BUCKET_NAME = "cookies-c4"

API_URL = "https://app.securiti.ai/reporting/v1/sources/query?ref=getCmpCookieConsentRecords"

# Carregar credenciais da API do arquivo secrets.toml
ORGANIZATIONS = {
    "property": {
        "x-api-key": st.secrets["api"]["property_api_key"],
        "x-api-secret": st.secrets["api"]["property_api_secret"],
        "x-org-id": st.secrets["api"]["property_org_id"]
    },
    "carrefour": {
        "x-api-key": st.secrets["api"]["carrefour_api_key"],
        "x-api-secret": st.secrets["api"]["carrefour_api_secret"],
        "x-org-id": st.secrets["api"]["carrefour_org_id"]
    },
    "sams": {
        "x-api-key": st.secrets["api"]["sams_api_key"],
        "x-api-secret": st.secrets["api"]["sams_api_secret"],
        "x-org-id": st.secrets["api"]["sams_org_id"]
    },
    "cci": {
        "x-api-key": st.secrets["api"]["cci_api_key"],
        "x-api-secret": st.secrets["api"]["cci_api_secret"],
        "x-org-id": st.secrets["api"]["cci_org_id"]
    }
}

# Carregar credenciais do banco de dados
mongo_user = st.secrets["database"]["user"]
mongo_password = st.secrets["database"]["password"]

db = conectaBanco(mongo_user, mongo_password)
consolidado_collection = db["consolidado_cookies"]


def list_blobs(bucket_name):
    """Lista os arquivos dentro de um bucket do Google Cloud Storage."""
    blobs = client.list_blobs(bucket_name)
    return [blob.name for blob in blobs]

def upload_parquet_gcs(df, filename):
    """Faz upload de um DataFrame como Parquet no Google Cloud Storage (GCS)."""
    try:
        output = io.BytesIO()
        df.to_parquet(output, engine="pyarrow")
        output.seek(0)
        blob = client.bucket(GCS_BUCKET_NAME).blob(filename)
        blob.upload_from_file(output, content_type="application/octet-stream")
        st.write(f"📤 Arquivo {filename} enviado para GCS!")
    except Exception as e:
        st.error(f"Erro ao fazer upload para o Google Cloud Storage: {e}")

def fetch_missing_data():
    """Verifica e busca dados ausentes desde 01/03/24 até o dia anterior ao atual."""
    start_date = datetime(2024, 6, 1)
    end_date = datetime.now() - timedelta(days=1)
    existing_blobs = set(list_blobs(GCS_BUCKET_NAME))
    
    while start_date <= end_date:
        filename = f"cookies_{start_date.strftime('%Y-%m-%d')}.parquet"
        if filename not in existing_blobs:
            st.write(f"📅 Buscando dados para {start_date.strftime('%Y-%m-%d')}...")
            df = fetch_cookie_data(start_date, start_date + timedelta(days=1))
            if not df.empty:
                upload_parquet_gcs(df, filename)
                st.write(f"✅ Dados de {start_date.strftime('%Y-%m-%d')} processados e enviados para o bucket.")
            else:
                st.write(f"⚠️ Nenhum dado encontrado para {start_date.strftime('%Y-%m-%d')}")
        else:
            st.write(f"✔️ Dados de {start_date.strftime('%Y-%m-%d')} já existem no bucket. Pulando...")
        
        start_date += timedelta(days=1)

def fetch_cookie_data(start_date, end_date):
    """Baixa dados de cookies para um intervalo de tempo específico."""
    all_data = []
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    
    for org_name, credentials in ORGANIZATIONS.items():
        offset = 0
        batch_size = 100000  # Reduzindo tamanho do lote para evitar erros 502
        while True:
            st.write(f"⏳ Buscando dados para {org_name}, {start_date.strftime('%Y-%m-%d')}, offset {offset}, batch {batch_size}...")
            headers = {
                "x-tident": st.secrets["api"]["x_tident"],
                "x-api-key": credentials["x-api-key"],
                "x-api-secret": credentials["x-api-secret"],
                "x-org-id": credentials["x-org-id"]
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
                    {"name": "consent_ip_address"}, {"name": "gpc_signal"}, {"name": "consent_geo_location_country"}
                ],
                "order_by": ["-activity_timestamp"],
                "skip_cache": True,
                "filter": {
                    "op": "and",
                    "value": [
                        {"op": "gte", "field": "activity_timestamp", "value": start_ts},
                        {"op": "lt", "field": "activity_timestamp", "value": end_ts}
                    ]
                }
            }
            
            response = requests.post(API_URL, json=payload, headers=headers, verify=False)
            st.write(f"🔍 Resposta da API para {org_name} ({response.status_code})")
            
            if response.status_code == 200:
                data = response.json()
                records = data.get("data", [])
                st.write(f"✅ {len(records)} registros recebidos para {org_name}")
                if not records:
                    break
                for record in records:
                    record["organization"] = org_name
                all_data.extend(records)
                offset += batch_size
            else:
                st.error(f"❌ Erro ao buscar dados para {org_name}: {response.status_code} - {response.text}")
                break
    
    return pd.DataFrame(all_data)

def calcular_metricas(df, data_ref):
    """Calcula métricas consolidadas de consentimento por organização."""
    resultados = []
    orgs = df['organization'].unique()
    for org in orgs:
        subset = df[df['organization'] == org]
        metricas = {
            "date": data_ref.strftime("%Y-%m-%d"),
            "organization": org,
            "metrics": {
                "total_consents": subset['consent_id'].nunique(),
                "unique_users": subset['user_uuid'].nunique(),
                "implicit_ratio": float((subset['implicit_consent'] == True).sum() / len(subset)),
                "gpc_enabled": int((subset['gpc_signal'] == True).sum()),
                "categories": subset['consent_scanned_props_category'].value_counts().to_dict(),
                "countries": subset['consent_geo_location_country'].value_counts().to_dict(),
                "domains": subset['domain_url'].value_counts().to_dict()
            }
        }
        resultados.append(metricas)
    return resultados

def processar_para_mongo():
    start_date = datetime(2024, 3, 1)
    end_date = datetime.now() - timedelta(days=1)
    existing_blobs = set(list_blobs(GCS_BUCKET_NAME))

    while start_date <= end_date:
        filename = f"cookies_{start_date.strftime('%Y-%m-%d')}.parquet"

        if filename not in existing_blobs:
            st.write(f"❌ Arquivo {filename} não existe no GCS. Pulando...")
        else:
            exists = consolidado_collection.find_one({"date": start_date.strftime("%Y-%m-%d")})
            if exists:
                st.write(f"✔️ Consolidado de {start_date.strftime('%Y-%m-%d')} já existe no Mongo. Pulando...")
            else:
                st.write(f"📊 Gerando consolidado para {start_date.strftime('%Y-%m-%d')}...")
                blob = client.bucket(GCS_BUCKET_NAME).blob(filename)
                buffer = io.BytesIO()
                blob.download_to_file(buffer)
                buffer.seek(0)
                df = pd.read_parquet(buffer)
                metricas = calcular_metricas(df, start_date)
                consolidado_collection.insert_many(metricas)
                st.write(f"✅ Consolidado de {start_date.strftime('%Y-%m-%d')} inserido no MongoDB.")

        start_date += timedelta(days=1)