"""
DAG: doomijn_scrape
Scrapt vacatures van komwerkenbij.doomijn.nl (Teamtailor RSS) elke dag om 06:45.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_scraper():
    from scrapers.doomijn import DoomijnScraper
    stats = DoomijnScraper().run()
    print(f"Resultaat: {stats}")
    return stats


with DAG(
    dag_id="doomijn_scrape",
    description="Scrapt vacatures van Doomijn Kinderopvang (Teamtailor RSS)",
    schedule=None,
    is_paused_upon_creation=True,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=15),
    },
    tags=["scraping", "doomijn", "teamtailor"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_doomijn",
        python_callable=run_scraper,
    )
