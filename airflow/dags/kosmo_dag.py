"""DAG: kosmo_scrape — dagelijkse scrape van KosmoScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kosmo import KosmoScraper
    stats = KosmoScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kosmo_scrape",
    description="Dagelijkse scrape van KosmoScraper",
    schedule="55 11 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "kosmo"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kosmo",
        python_callable=run_scraper,
    )
