"""DAG: junis_scrape — dagelijkse scrape van JunisScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.junis import JunisScraper
    stats = JunisScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="junis_scrape",
    description="Dagelijkse scrape van JunisScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "junis"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_junis",
        python_callable=run_scraper,
    )
