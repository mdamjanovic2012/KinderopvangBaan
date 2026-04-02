"""
DAG: gro_up_scrape
Scrapt vacatures van werkenbijgro-up.nl (Teamtailor RSS) elke dag om 06:35.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.gro_up import GroUpScraper
    stats = GroUpScraper().run()
    print(f"Resultaat: {stats}")
    return stats


with DAG(
    dag_id="gro_up_scrape",
    description="Scrapt vacatures van Gro-up kinderopvang (Teamtailor RSS)",
    schedule="35 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=15),
    },
    tags=["scraping", "gro-up", "teamtailor"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_gro_up",
        python_callable=run_scraper,
    )
