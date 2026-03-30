"""
DAG: partou_scrape
Scrapt vacatures van werkenbijpartou.nl elke dag om 06:30.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.partou import PartouScraper
    stats = PartouScraper().run()
    print(f"Resultaat: {stats}")
    return stats


with DAG(
    dag_id="partou_scrape",
    description="Scrapt vacatures van Partou (werkenbijpartou.nl)",
    schedule="30 6 * * *",       # elke dag om 06:30 (30min na Kinderdam)
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "partou"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_partou",
        python_callable=run_scraper,
    )
