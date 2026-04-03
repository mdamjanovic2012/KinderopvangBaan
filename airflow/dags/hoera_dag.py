"""DAG: hoera_scrape — dagelijkse scrape van HoeraScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.hoera import HoeraScraper
    stats = HoeraScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="hoera_scrape",
    description="Dagelijkse scrape van HoeraScraper",
    schedule="17 10 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "hoera"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_hoera",
        python_callable=run_scraper,
    )
