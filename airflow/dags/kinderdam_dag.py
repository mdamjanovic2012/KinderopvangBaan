"""
DAG: kinderdam_scrape
Scrapt vacatures van ikwerkaandetoekomst.nl (Kinderdam) elke dag om 06:00.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kinderdam import KinderdamScraper
    stats = KinderdamScraper().run()
    print(f"Resultaat: {stats}")
    return stats


with DAG(
    dag_id="kinderdam_scrape",
    description="Scrapt vacatures van Kinderdam (ikwerkaandetoekomst.nl)",
    schedule="0 6 * * *",        # elke dag om 06:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "kinderdam"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kinderdam",
        python_callable=run_scraper,
    )
