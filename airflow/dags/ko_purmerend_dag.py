"""DAG: ko_purmerend_scrape — dagelijkse scrape van KoPurmerendScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.ko_purmerend import KoPurmerendScraper
    stats = KoPurmerendScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="ko_purmerend_scrape",
    description="Dagelijkse scrape van KoPurmerendScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "ko_purmerend"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_ko_purmerend",
        python_callable=run_scraper,
    )
