"""DAG: solidoe_scrape — dagelijkse scrape van SolidoeScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.solidoe import SolidoeScraper
    stats = SolidoeScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="solidoe_scrape",
    description="Dagelijkse scrape van SolidoeScraper",
    schedule="40 13 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "solidoe"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_solidoe",
        python_callable=run_scraper,
    )
