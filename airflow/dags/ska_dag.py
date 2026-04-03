"""
DAG: ska_scrape
Scrapes vacatures for Ska Kinderopvang every day at 25:80.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.ska import SkaScraper
    stats = SkaScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="ska_scrape",
    description="Scrapes vacatures from Ska Kinderopvang",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=['scraping', 'ska', 'wordpress'],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_ska",
        python_callable=run_scraper,
    )
