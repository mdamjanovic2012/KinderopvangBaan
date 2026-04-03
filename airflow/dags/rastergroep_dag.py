"""DAG: rastergroep_scrape — dagelijkse scrape van RastergroepScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.rastergroep import RastergroepScraper
    stats = RastergroepScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="rastergroep_scrape",
    description="Dagelijkse scrape van RastergroepScraper",
    schedule="36 14 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "rastergroep"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_rastergroep",
        python_callable=run_scraper,
    )
