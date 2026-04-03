"""
DAG: prokino_scrape
Scrapes vacatures from werkenbij.prokino.nl every day at 07:30.
Uses Playwright for AFAS OutSite JavaScript rendering.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.prokino import ProkinoScraper
    stats = ProkinoScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="prokino_scrape",
    description="Scrapes vacatures from Prokino (AFAS OutSite)",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=60),
    },
    tags=["scraping", "prokino", "playwright", "afas"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_prokino",
        python_callable=run_scraper,
    )
