"""DAG: kleurrijk_scrape — dagelijkse scrape van KleurrijkScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kleurrijk import KleurrijkScraper
    stats = KleurrijkScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kleurrijk_scrape",
    description="Dagelijkse scrape van KleurrijkScraper",
    schedule="20 11 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "kleurrijk"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kleurrijk",
        python_callable=run_scraper,
    )
