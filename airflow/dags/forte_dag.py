"""DAG: forte_scrape — dagelijkse scrape van ForteScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.forte import ForteScraper
    stats = ForteScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="forte_scrape",
    description="Dagelijkse scrape van ForteScraper",
    schedule="42 9 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "forte"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_forte",
        python_callable=run_scraper,
    )
