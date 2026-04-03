"""
DAG: kanteel_scrape
Scrapes vacatures for Kanteel Kinderopvang every day at 15:08.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kanteel import KanteelScraper
    stats = KanteelScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kanteel_scrape",
    description="Scrapes vacatures from Kanteel Kinderopvang",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=['scraping', 'kanteel', 'wordpress'],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kanteel",
        python_callable=run_scraper,
    )
