import streamlit as st
from google.cloud import storage
from google.oauth2.service_account import Credentials

def list_blobs(bucket_name):
    """Lista todos os blobs no bucket."""
    # Carregar as credenciais do `secrets.toml`
    credentials = Credentials.from_service_account_info(
        st.secrets["google_cloud"]
    )
    storage_client = storage.Client(credentials=credentials)

    # Note: Client.list_blobs requires at least package version 1.17.0.
    blobs = storage_client.list_blobs(bucket_name)

    for blob in blobs:
        print(blob.name)

# Substitua 'cookies-c4' pelo nome do seu bucket
list_blobs('cookies-c4')
