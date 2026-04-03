"""DAG: kids2b_scrape — dagelijkse scrape van Kids2bScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.kids2b import Kids2bScraper
    stats = Kids2bScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="kids2b_scrape",
    description="Dagelijkse scrape van Kids2bScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "kids2b"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_kids2b",
        python_callable=run_scraper,
    )
