"""
Backfill ÚNICO: recalcula os documentos de `consolidado_cookies` que foram
gravados ANTES da correção do cruzamento domínio x categoria (ou seja, que
não têm o campo `metrics.domain_categories`), reprocessando o parquet bruto
do dia direto do GCS e substituindo o documento.

Rode uma vez, manualmente, depois de já ter feito o deploy da correção
(ou dispare pela aba Actions do GitHub, via workflow_dispatch, ver
.github/workflows/backfill-domain-categories.yml).

Uso local:
    cd scripts
    export MONGO_USER=...
    export MONGO_PASSWORD=...
    export GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type": "service_account", ...}'
    python backfill_domain_categories.py
"""

import io
import sys
from datetime import datetime

import pandas as pd

from common import conecta_banco, logger
from sync_cookies import _gcs_client, calcular_metricas, GCS_BUCKET_NAME


def main():
    collection = conecta_banco()
    consolidado = collection["consolidado_cookies"]
    gcs_client = _gcs_client()

    docs_sem_detalhe = list(consolidado.find({"metrics.domain_categories": {"$exists": False}}))
    datas = sorted({doc["date"] for doc in docs_sem_detalhe})
    logger.info("Documentos sem o cruzamento novo: %d (%d dias distintos)", len(docs_sem_detalhe), len(datas))

    if not datas:
        logger.info("Nada para reprocessar — todos os documentos já têm domain_categories.")
        return

    atualizados = 0
    pulados = 0
    for data_str in datas:
        filename = f"cookies_{data_str}.parquet"
        blob = gcs_client.bucket(GCS_BUCKET_NAME).blob(filename)
        if not blob.exists():
            logger.warning("Parquet %s não encontrado no GCS — pulando esse dia.", filename)
            pulados += 1
            continue

        buffer = io.BytesIO()
        blob.download_to_file(buffer)
        buffer.seek(0)
        df = pd.read_parquet(buffer)

        data_ref = datetime.strptime(data_str, "%Y-%m-%d")
        metricas = calcular_metricas(df, data_ref)

        for m in metricas:
            resultado = consolidado.update_one(
                {"date": m["date"], "organization": m["organization"]},
                {"$set": {"metrics": m["metrics"]}},
            )
            if resultado.matched_count:
                atualizados += 1
            else:
                # Não existia documento pra essa organização nesse dia (raro) — insere.
                consolidado.insert_one(m)
                atualizados += 1

        logger.info("Reprocessado: %s", data_str)

    logger.info(
        "Backfill concluído. Documentos atualizados/inseridos: %d. Dias pulados (sem parquet no GCS): %d.",
        atualizados, pulados,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Backfill de domain_categories falhou")
        sys.exit(1)
