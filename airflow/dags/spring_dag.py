"""
DAG: spring_scrape
Scrapt vacatures van werkenbijspring.nl elke dag om 06:40.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.spring_kinderopvang import SpringKinderopvangScraper
    stats = SpringKinderopvangScraper().run()
    print(f"Resultaat: {stats}")
    return stats


with DAG(
    dag_id="spring_scrape",
    description="Scrapt vacatures van Spring Kinderopvang (werkenbijspring.nl)",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "spring"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_spring",
        python_callable=run_scraper,
    )
