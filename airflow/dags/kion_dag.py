"""
DAG: kion_scrape
Scrapes vacatures from werkenbijkion.nl every day at 07:45.
Uses Recruitee public API (no HTML scraping).
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kion import KIONScraper
    stats = KIONScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kion_scrape",
    description="Scrapes vacatures from KION Kinderopvang (Recruitee API)",
    schedule="45 7 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=15),
    },
    tags=["scraping", "kion", "recruitee"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kion",
        python_callable=run_scraper,
    )
