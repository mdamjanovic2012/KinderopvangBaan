"""
DAG: mik_scrape
Scrapes vacatures from werkenbijmikenpiwgroep.nl every day at 08:05.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.mik import MIKScraper
    stats = MIKScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="mik_scrape",
    description="Scrapes vacatures from MIK & PIW Groep",
    schedule="5 8 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "mik", "wordpress"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_mik",
        python_callable=run_scraper,
    )
