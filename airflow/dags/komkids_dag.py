"""DAG: komkids_scrape — dagelijkse scrape van KomKidsScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.komkids import KomKidsScraper
    stats = KomKidsScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="komkids_scrape",
    description="Dagelijkse scrape van KomKidsScraper",
    schedule="41 11 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "komkids"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_komkids",
        python_callable=run_scraper,
    )
