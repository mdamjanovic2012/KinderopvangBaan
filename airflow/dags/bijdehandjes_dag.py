"""
DAG: bijdehandjes_scrape
Scrapes vacatures for BijdeHandjes every day at 15:08.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.bijdehandjes import BijdeHandjesScraper
    stats = BijdeHandjesScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="bijdehandjes_scrape",
    description="Scrapes vacatures from BijdeHandjes",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=['scraping', 'bijdehandjes', 'wordpress'],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_bijdehandjes",
        python_callable=run_scraper,
    )
