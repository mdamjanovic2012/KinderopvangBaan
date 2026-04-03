"""DAG: morgen_scrape — dagelijkse scrape van MorgenScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.morgen import MorgenScraper
    stats = MorgenScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="morgen_scrape",
    description="Dagelijkse scrape van MorgenScraper",
    schedule="23 12 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "morgen"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_morgen",
        python_callable=run_scraper,
    )
