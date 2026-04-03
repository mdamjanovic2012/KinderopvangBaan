"""DAG: monkey_donky_scrape — dagelijkse scrape van MonkeyDonkyScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.monkey_donky import MonkeyDonkyScraper
    stats = MonkeyDonkyScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="monkey_donky_scrape",
    description="Dagelijkse scrape van MonkeyDonkyScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "monkey_donky"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_monkey_donky",
        python_callable=run_scraper,
    )
