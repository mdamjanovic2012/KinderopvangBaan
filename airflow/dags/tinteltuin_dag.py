"""
DAG: tinteltuin_scrape
Scrapes vacatures from tinteltuin.nl every day at 07:15.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.tinteltuin import TintelTuinScraper
    stats = TintelTuinScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="tinteltuin_scrape",
    description="Scrapes vacatures from TintelTuin",
    schedule="15 7 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "tinteltuin", "wordpress"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_tinteltuin",
        python_callable=run_scraper,
    )
