"""DAG: woest_zuid_scrape — dagelijkse scrape van WoestZuidScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.woest_zuid import WoestZuidScraper
    stats = WoestZuidScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="woest_zuid_scrape",
    description="Dagelijkse scrape van WoestZuidScraper",
    schedule="15 14 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "woest_zuid"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_woest_zuid",
        python_callable=run_scraper,
    )
