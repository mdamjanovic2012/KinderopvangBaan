"""
DAG: dak_scrape
Scrapes vacatures from dakkindercentra.nl every day at 07:20.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.dak import DakScraper
    stats = DakScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="dak_scrape",
    description="Scrapes vacatures from Dak Kindercentra",
    schedule="20 7 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "dak", "wordpress"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_dak",
        python_callable=run_scraper,
    )
