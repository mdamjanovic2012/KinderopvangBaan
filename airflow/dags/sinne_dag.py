"""
DAG: sinne_scrape
Scrapes vacatures from sinne.easycruit.com every day at 07:35.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.sinne import SinneScraper
    stats = SinneScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="sinne_scrape",
    description="Scrapes vacatures from Sinne Kinderopvang (EasyCruit)",
    schedule="35 7 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "sinne", "easycruit"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_sinne",
        python_callable=run_scraper,
    )
