"""DAG: kinderstad_scrape — dagelijkse scrape van KinderstadScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kinderstad import KinderstadScraper
    stats = KinderstadScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kinderstad_scrape",
    description="Dagelijkse scrape van KinderstadScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "kinderstad"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kinderstad",
        python_callable=run_scraper,
    )
