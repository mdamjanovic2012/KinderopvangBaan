"""DAG: ksh_scrape — dagelijkse scrape van KshScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.ksh import KshScraper
    stats = KshScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="ksh_scrape",
    description="Dagelijkse scrape van KshScraper",
    schedule="2 12 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "ksh"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_ksh",
        python_callable=run_scraper,
    )
