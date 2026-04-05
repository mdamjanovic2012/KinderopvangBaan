"""DAG: de_lange_keizer_scrape — dagelijkse scrape van DeLangeKeizerScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.de_lange_keizer import DeLangeKeizerScraper
    stats = DeLangeKeizerScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="de_lange_keizer_scrape",
    description="Dagelijkse scrape van DeLangeKeizerScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "de_lange_keizer"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_de_lange_keizer",
        python_callable=run_scraper,
    )
