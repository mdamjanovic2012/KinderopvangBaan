FROM apache/airflow:2.9.2-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# DAGs en scraper code
COPY dags/       /opt/airflow/dags/
COPY scrapers/   /opt/airflow/scrapers/
COPY db/         /opt/airflow/db/

# Python path zodat 'from scrapers.x import y' werkt in DAGs
ENV PYTHONPATH="/opt/airflow"

EXPOSE 8080
