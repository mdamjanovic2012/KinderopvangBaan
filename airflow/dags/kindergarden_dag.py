"""
DAG: kindergarden_scrape
Scrapes vacatures from werkenbijkindergarden.nl every day at 08:10.
Uses Playwright for listing page, requests for detail pages.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kindergarden import KindergardenScraper
    stats = KindergardenScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kindergarden_scrape",
    description="Scrapes vacatures from Kindergarden (Playwright listing + JSON-LD details)",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "kindergarden", "playwright", "jsonld"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kindergarden",
        python_callable=run_scraper,
    )
