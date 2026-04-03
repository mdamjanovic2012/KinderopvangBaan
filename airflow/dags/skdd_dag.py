"""DAG: skdd_scrape — dagelijkse scrape van SkddScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.skdd import SkddScraper
    stats = SkddScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="skdd_scrape",
    description="Dagelijkse scrape van SkddScraper",
    schedule="26 13 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "skdd"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_skdd",
        python_callable=run_scraper,
    )
