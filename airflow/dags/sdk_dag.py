"""DAG: sdk_scrape — dagelijkse scrape van SdkScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.sdk import SdkScraper
    stats = SdkScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="sdk_scrape",
    description="Dagelijkse scrape van SdkScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "sdk"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_sdk",
        python_callable=run_scraper,
    )
