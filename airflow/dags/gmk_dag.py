"""DAG: gmk_scrape — dagelijkse scrape van GmkScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.gmk import GmkScraper
    stats = GmkScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="gmk_scrape",
    description="Dagelijkse scrape van GmkScraper",
    schedule="49 9 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "gmk"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_gmk",
        python_callable=run_scraper,
    )
