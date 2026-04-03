"""
DAG: kober_scrape
Scrapes vacatures from werkenbijkober.nl every day at 07:10.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kober import KoberScraper
    stats = KoberScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kober_scrape",
    description="Scrapes vacatures from Kober Kinderopvang",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "kober", "wordpress"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kober",
        python_callable=run_scraper,
    )
