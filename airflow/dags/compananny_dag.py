"""
DAG: compananny_scrape
Scrapes vacatures from werkenbijcompananny.nl every day at 07:25.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.compananny import CompaNannyScraper
    stats = CompaNannyScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="compananny_scrape",
    description="Scrapes vacatures from CompaNanny",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=60),
    },
    tags=["scraping", "compananny", "jsonld"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_compananny",
        python_callable=run_scraper,
    )
