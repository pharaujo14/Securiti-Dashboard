# Importa a classe MongoClient da biblioteca pymongo.
# Isso nos permitirá conectar a um banco de dados MongoDB.
import streamlit as st
from pymongo import MongoClient


@st.cache_resource(show_spinner=False)
def conectaBanco(username, password):
    """Cria (uma única vez por processo, graças ao cache_resource) a conexão
    com o MongoDB e retorna a collection principal do dashboard.

    Antes, essa função rodava do zero a cada rerun do Streamlit (toda vez que
    alguém trocava um filtro), abrindo uma conexão nova cada vez. Com
    st.cache_resource, o mesmo cliente/conexão é reaproveitado entre reruns,
    o que deixa a navegação bem mais rápida.
    """
    client = MongoClient(
        f'mongodb+srv://{username}:{password}@centurydatamongocluster.k5fsf.mongodb.net/?retryWrites=true&w=majority&appName=CenturyDataMongoCluster'
    )
    db = client["Carrefour"]
    return db["dashboard_blackfriday"]


@st.cache_resource(show_spinner=False)
def conectaBancoRaw(username, password):
    """Igual à anterior, mas retorna o database inteiro (não só uma collection),
    para telas que precisam acessar outras collections (histórico, usuários,
    cookies consolidados etc.) sem abrir uma segunda conexão."""
    client = MongoClient(
        f'mongodb+srv://{username}:{password}@centurydatamongocluster.k5fsf.mongodb.net/?retryWrites=true&w=majority&appName=CenturyDataMongoCluster'
    )
    return client["Carrefour"]
