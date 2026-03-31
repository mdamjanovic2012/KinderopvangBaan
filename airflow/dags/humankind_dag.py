"""
DAG: humankind_scrape
Scrapes vacatures from werkenbijhumankind.nl every day at 07:40.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.humankind import HumankindScraper
    stats = HumankindScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="humankind_scrape",
    description="Scrapes vacatures from Humankind Kinderopvang",
    schedule="40 7 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=60),
    },
    tags=["scraping", "humankind", "jsonld"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_humankind",
        python_callable=run_scraper,
    )
