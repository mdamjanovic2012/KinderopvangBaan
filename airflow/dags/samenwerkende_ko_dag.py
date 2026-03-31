"""
DAG: samenwerkende_ko_scrape
Scrapt vacatures van samenwerkendekinderopvang.nl elke dag om 07:00.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.samenwerkende_ko import SamenwerkendeKOScraper
    stats = SamenwerkendeKOScraper().run()
    print(f"Resultaat: {stats}")
    return stats


with DAG(
    dag_id="samenwerkende_ko_scrape",
    description="Scrapt vacatures van Samenwerkende Kinderopvang",
    schedule="0 7 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "samenwerkende-ko", "wordpress"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_samenwerkende_ko",
        python_callable=run_scraper,
    )
