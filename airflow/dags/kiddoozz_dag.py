"""DAG: kiddoozz_scrape — dagelijkse scrape van KiddoozzScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kiddoozz import KiddoozzScraper
    stats = KiddoozzScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kiddoozz_scrape",
    description="Dagelijkse scrape van KiddoozzScraper",
    schedule="31 10 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "kiddoozz"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kiddoozz",
        python_callable=run_scraper,
    )
