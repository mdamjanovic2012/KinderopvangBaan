"""DAG: kindernet_scrape — dagelijkse scrape van KindernetScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kindernet import KindernetScraper
    stats = KindernetScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kindernet_scrape",
    description="Dagelijkse scrape van KindernetScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "kindernet"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kindernet",
        python_callable=run_scraper,
    )
