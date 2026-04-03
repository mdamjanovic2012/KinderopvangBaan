"""DAG: wildewijs_scrape — dagelijkse scrape van WildewijsScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.wildewijs import WildewijsScraper
    stats = WildewijsScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="wildewijs_scrape",
    description="Dagelijkse scrape van WildewijsScraper",
    schedule="8 14 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "wildewijs"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_wildewijs",
        python_callable=run_scraper,
    )
