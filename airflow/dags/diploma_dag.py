"""
DAG: diploma_update
Importeert diploma's van kinderopvang-werkt.nl API.
Draait max 1x per 180 dagen (throttle via airflow_sentinel tabel).

Vervanger van: backend/startup.sh update_diplomas + diploma-update.yml pipeline.
Logica zit in scrapers/diploma.py.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from scrapers.diploma import run_diploma_update

with DAG(
    dag_id="diploma_update",
    description="Importeert diploma's van kinderopvang-werkt.nl (max 1x per 180 dagen)",
    schedule="0 5 * * 1",        # elke maandag 05:00 — check of update nodig is
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
        "execution_timeout": timedelta(minutes=20),
    },
    tags=["diplomas"],
) as dag:

    update = PythonOperator(
        task_id="run_diploma_update",
        python_callable=run_diploma_update,
        op_kwargs={"force": False},
    )
