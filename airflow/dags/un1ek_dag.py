"""DAG: un1ek_scrape — dagelijkse scrape van Un1ekScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.un1ek import Un1ekScraper
    stats = Un1ekScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="un1ek_scrape",
    description="Dagelijkse scrape van Un1ekScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "un1ek"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_un1ek",
        python_callable=run_scraper,
    )
