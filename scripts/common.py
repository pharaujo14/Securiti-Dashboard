"""
Utilidades compartilhadas pelos scripts de sincronização (sync_dsar.py e sync_cookies.py).

Esses scripts rodam FORA do Streamlit (via GitHub Actions), então usam variáveis de
ambiente em vez de st.secrets. Isso permite rodar o mesmo código tanto localmente
(exportando as variáveis, ou com um .env) quanto no runner do GitHub Actions
(via "Repository secrets").
"""

import os
import sys
import logging

from pymongo import MongoClient
from pymongo.errors import PyMongoError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("century-data-sync")


def get_env(name: str, required: bool = True, default: str = None) -> str:
    """Lê uma variável de ambiente. Se for obrigatória e estiver ausente,
    encerra o script com código de erro != 0 (assim o GitHub Actions marca
    o job como falho e pode notificar por e-mail)."""
    value = os.environ.get(name, default)
    if required and not value:
        logger.error("Variável de ambiente obrigatória ausente: %s", name)
        sys.exit(1)
    return value


def conecta_banco():
    """Conecta no MongoDB e retorna a collection 'dashboard_blackfriday'.

    Atenção a um detalhe importante do projeto original (utils/conectaBanco.py):
    o app NÃO trabalha com o database inteiro — ele trabalha com a collection
    "dashboard_blackfriday", e todo o resto (historico_atualizacoes, users,
    consolidado_cookies) é acessado como sub-coleção dela, ex.: collection['users'].
    No pymongo isso cria, na prática, uma collection com nome pontuado
    "dashboard_blackfriday.users" — não uma collection "users" de nível superior.
    Por isso esta função devolve a collection "dashboard_blackfriday" (e não o
    database), pra quem for usá-la continuar acessando exatamente os mesmos
    lugares que o app já lê/escreve hoje.
    """
    user = get_env("MONGO_USER")
    password = get_env("MONGO_PASSWORD")

    uri = (
        f"mongodb+srv://{user}:{password}"
        "@centurydatamongocluster.k5fsf.mongodb.net/"
        "?retryWrites=true&w=majority&appName=CenturyDataMongoCluster"
    )

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=15000)
        # Força uma checagem de conexão agora, para falhar rápido e de forma
        # visível no log do Actions, em vez de falhar silenciosamente mais tarde.
        client.admin.command("ping")
    except PyMongoError as exc:
        logger.error("Não foi possível conectar ao MongoDB: %s", exc)
        sys.exit(1)

    db = client["Carrefour"]
    return db["dashboard_blackfriday"]
