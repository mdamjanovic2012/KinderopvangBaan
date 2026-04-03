"""DAG: lps_scrape — dagelijkse scrape van LpsScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.lps import LpsScraper
    stats = LpsScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="lps_scrape",
    description="Dagelijkse scrape van LpsScraper",
    schedule="9 12 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "lps"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_lps",
        python_callable=run_scraper,
    )
