"""
DAG: twee_samen_scrape
Scrapes vacatures from werkenbij2samen.nl every day at 07:55.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.twee_samen import TweeSamenScraper
    stats = TweeSamenScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="twee_samen_scrape",
    description="Scrapes vacatures from 2Samen Kinderopvang",
    schedule="55 7 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=60),
    },
    tags=["scraping", "2samen", "wordpress"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_twee_samen",
        python_callable=run_scraper,
    )
