"""DAG: sportstuif_scrape — dagelijkse scrape van SportstuifScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.sportstuif import SportstuifScraper
    stats = SportstuifScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="sportstuif_scrape",
    description="Dagelijkse scrape van SportstuifScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "sportstuif"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_sportstuif",
        python_callable=run_scraper,
    )
