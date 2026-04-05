"""DAG: atalenta_scrape — dagelijkse scrape van AtalentaScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.atalenta import AtalentaScraper
    stats = AtalentaScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="atalenta_scrape",
    description="Dagelijkse scrape van AtalentaScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "atalenta"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_atalenta",
        python_callable=run_scraper,
    )
