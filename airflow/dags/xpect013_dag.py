"""DAG: xpect013_scrape — dagelijkse scrape van Xpect013Scraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.xpect013 import Xpect013Scraper
    stats = Xpect013Scraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="xpect013_scrape",
    description="Dagelijkse scrape van Xpect013Scraper",
    schedule="22 14 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "xpect013"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_xpect013",
        python_callable=run_scraper,
    )
