"""DAG: de_eerste_stap_scrape — dagelijkse scrape van DeEersteStapScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.de_eerste_stap import DeEersteStapScraper
    stats = DeEersteStapScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="de_eerste_stap_scrape",
    description="Dagelijkse scrape van DeEersteStapScraper",
    schedule="14 9 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "de_eerste_stap"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_de_eerste_stap",
        python_callable=run_scraper,
    )
