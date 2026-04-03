"""
DAG: kibeo_scrape
Scrapes vacatures from werkenbijkibeo.nl (Kibeo, WiedeWei, Elorah, Junia, Kik)
every day at 07:05.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kibeo import KibeoScraper
    stats = KibeoScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kibeo_scrape",
    description="Scrapes vacatures from Kibeo (werkenbijkibeo.nl) via Playwright",
    schedule="5 7 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=60),
    },
    tags=["scraping", "kibeo", "playwright"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kibeo",
        python_callable=run_scraper,
    )
