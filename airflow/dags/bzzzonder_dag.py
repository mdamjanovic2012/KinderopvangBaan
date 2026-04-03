"""DAG: bzzzonder_scrape — dagelijkse scrape van BzzzonderScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.bzzzonder import BzzzonderScraper
    stats = BzzzonderScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="bzzzonder_scrape",
    description="Dagelijkse scrape van BzzzonderScraper",
    schedule="7 9 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "bzzzonder"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_bzzzonder",
        python_callable=run_scraper,
    )
