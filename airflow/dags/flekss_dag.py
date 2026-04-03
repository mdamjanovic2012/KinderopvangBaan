"""DAG: flekss_scrape — dagelijkse scrape van FlekssScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.flekss import FlekssScraper
    stats = FlekssScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="flekss_scrape",
    description="Dagelijkse scrape van FlekssScraper",
    schedule="28 9 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "flekss"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_flekss",
        python_callable=run_scraper,
    )
