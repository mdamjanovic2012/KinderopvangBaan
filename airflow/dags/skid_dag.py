"""DAG: skid_scrape — dagelijkse scrape van SkidScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.skid import SkidScraper
    stats = SkidScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="skid_scrape",
    description="Dagelijkse scrape van SkidScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "skid"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_skid",
        python_callable=run_scraper,
    )
