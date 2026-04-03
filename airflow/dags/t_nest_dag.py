"""DAG: t_nest_scrape — dagelijkse scrape van TNestScraper."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.t_nest import TNestScraper
    stats = TNestScraper().run()
    print(f"Result: {stats}")
    return stats


with DAG(
    dag_id="t_nest_scrape",
    description="Dagelijkse scrape van TNestScraper",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["scraping", "tnest"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_t_nest",
        python_callable=run_scraper,
    )
