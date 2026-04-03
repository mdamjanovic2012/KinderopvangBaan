"""
DAG: wij_zijn_jong_scrape
Scrapes vacatures from werkenbijwijzijnjong.nl every day at 07:50.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.wij_zijn_jong import WijZijnJONGScraper
    stats = WijZijnJONGScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="wij_zijn_jong_scrape",
    description="Scrapes vacatures from Wij zijn JONG (WordPress, paginated)",
    schedule="50 7 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=60),
    },
    tags=["scraping", "wij-zijn-jong", "wordpress"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_wij_zijn_jong",
        python_callable=run_scraper,
    )
