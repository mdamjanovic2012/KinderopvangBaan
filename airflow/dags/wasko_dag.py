"""
DAG: wasko_scrape
Scrapes vacatures for Wasko Kinderopvang every day at 30:80.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.wasko import WaskoScraper
    stats = WaskoScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="wasko_scrape",
    description="Scrapes vacatures from Wasko Kinderopvang",
    schedule="30 8 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=['scraping', 'wasko', 'wordpress'],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_wasko",
        python_callable=run_scraper,
    )
