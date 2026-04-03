"""DAG: puckco_scrape — dagelijkse scrape van PuckcoScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.puckco import PuckcoScraper
    stats = PuckcoScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="puckco_scrape",
    description="Dagelijkse scrape van PuckcoScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "puckco"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_puckco",
        python_callable=run_scraper,
    )
