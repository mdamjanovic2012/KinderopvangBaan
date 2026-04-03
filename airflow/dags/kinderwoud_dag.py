"""
DAG: kinderwoud_scrape
Scrapes vacatures for Kinderwoud every day at 20:80.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kinderwoud import KinderwoudScraper
    stats = KinderwoudScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kinderwoud_scrape",
    description="Scrapes vacatures from Kinderwoud",
    schedule="20 8 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=['scraping', 'kinderwoud', 'wordpress'],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kinderwoud",
        python_callable=run_scraper,
    )
