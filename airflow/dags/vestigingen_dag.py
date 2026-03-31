"""
DAG: branch_scrape
Scrapes precise addresses of childcare company branches from their websites.
Stores name + full address + coordinates in the jobs_vestiging table.
Used as a fallback for street-level geocoding of job vacancies.

Schedule: weekly on Monday at 04:00 (before daily job scrapes).
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_branch_scrape():
    from scrapers.branches import run_vestigingen_scrape
    stats = run_vestigingen_scrape()
    print(f"Branch scrape result: {stats}")
    return stats


with DAG(
    dag_id="branch_scrape",
    description="Scrapes branch addresses from company websites for precise geocoding",
    schedule="0 4 * * 1",        # every Monday at 04:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["enrichment", "geocoding", "branches"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_branches",
        python_callable=run_branch_scrape,
    )
