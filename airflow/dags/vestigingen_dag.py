"""
DAG: vestigingen_scrape
Scrapt precieze adressen van kinderopvang vestigingen van bedrijfswebsites.
Slaat naam + volledig adres + coördinaten op in jobs_vestiging tabel.
Wordt gebruikt als fallback voor precies geocoding van vacatures.

Schema: wekelijks op maandag om 04:00 (voor dagelijkse job scrapes).
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_vestigingen():
    from scrapers.vestigingen import run_vestigingen_scrape
    stats = run_vestigingen_scrape()
    print(f"Vestigingen resultaat: {stats}")
    return stats


with DAG(
    dag_id="vestigingen_scrape",
    description="Scrapt vestiging-adressen van bedrijfswebsites voor precies geocoding",
    schedule="0 4 * * 1",        # elke maandag om 04:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["enrichment", "geocoding", "vestigingen"],
) as dag:

    scrape = PythonOperator(
        task_id="scrape_vestigingen",
        python_callable=run_vestigingen,
    )
