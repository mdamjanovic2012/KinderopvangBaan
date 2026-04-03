"""DAG: ckc_drenthe_scrape — dagelijkse scrape van CKCDrentheScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.ckc_drenthe import CKCDrentheScraper
    stats = CKCDrentheScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="ckc_drenthe_scrape",
    description="Dagelijkse scrape van CKCDrentheScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "ckcdrenthe"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_ckc_drenthe",
        python_callable=run_scraper,
    )
