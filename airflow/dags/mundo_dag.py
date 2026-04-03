"""DAG: mundo — Mundo Kinderopvang vacature scraper."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_mundo():
    from scrapers.mundo import MundoScraper
    return MundoScraper().run()


with DAG(
    dag_id="mundo",
    description="Scrape Mundo Kinderopvang vacatures",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    tags=["scraping", "mundo"],
    is_paused_upon_creation=True,
) as dag:
    PythonOperator(task_id="scrape_mundo", python_callable=run_mundo)
