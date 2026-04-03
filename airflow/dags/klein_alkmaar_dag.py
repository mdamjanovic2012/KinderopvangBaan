"""DAG: klein_alkmaar_scrape — dagelijkse scrape van KleinAlkmaarScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.klein_alkmaar import KleinAlkmaarScraper
    stats = KleinAlkmaarScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="klein_alkmaar_scrape",
    description="Dagelijkse scrape van KleinAlkmaarScraper",
    schedule="13 11 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "klein_alkmaar"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_klein_alkmaar",
        python_callable=run_scraper,
    )
