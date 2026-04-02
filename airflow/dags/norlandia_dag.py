"""
DAG: norlandia_scrape
Scrapt vacatures van werkenbij.norlandia.nl (Teamtailor RSS) elke dag om 06:30.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.norlandia import NorlandiaScraper
    stats = NorlandiaScraper().run()
    print(f"Resultaat: {stats}")
    return stats


with DAG(
    dag_id="norlandia_scrape",
    description="Scrapt vacatures van Norlandia kinderopvang (Teamtailor RSS)",
    schedule="30 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=15),
    },
    tags=["scraping", "norlandia", "teamtailor"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_norlandia",
        python_callable=run_scraper,
    )
