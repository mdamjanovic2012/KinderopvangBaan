"""
DAG: ko_walcheren_scrape
Scrapes vacatures for Kinderopvang Walcheren every day at 40:80.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.ko_walcheren import KOWalcherenScraper
    stats = KOWalcherenScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="ko_walcheren_scrape",
    description="Scrapes vacatures from Kinderopvang Walcheren",
    schedule="40 8 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=['scraping', 'ko-walcheren', 'wordpress'],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_ko_walcheren",
        python_callable=run_scraper,
    )
