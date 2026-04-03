"""
DAG: op_stoom_scrape
Scrapes vacatures for Op Stoom Kinderopvang every day at 35:80.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.op_stoom import OpStoomScraper
    stats = OpStoomScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="op_stoom_scrape",
    description="Scrapes vacatures from Op Stoom Kinderopvang",
    schedule="35 8 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=['scraping', 'op-stoom', 'wordpress'],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_op_stoom",
        python_callable=run_scraper,
    )
