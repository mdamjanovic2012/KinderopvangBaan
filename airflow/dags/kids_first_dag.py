"""
DAG: kids_first_scrape
Scrapes vacatures from werkenbijkidsfirst.nl every day at 08:00.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kids_first import KidsFirstScraper
    stats = KidsFirstScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kids_first_scrape",
    description="Scrapes vacatures from Kids First Kinderopvang",
    schedule="0 8 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "kids-first", "wordpress"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kids_first",
        python_callable=run_scraper,
    )
