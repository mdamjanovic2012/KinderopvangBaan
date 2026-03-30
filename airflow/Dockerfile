FROM apache/airflow:2.9.2-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Installeer Playwright Chromium browser binary (system deps al geïnstalleerd hierboven)
RUN playwright install chromium

# DAGs en scraper code
COPY dags/       /opt/airflow/dags/
COPY scrapers/   /opt/airflow/scrapers/
COPY db/         /opt/airflow/db/

# Python path zodat 'from scrapers.x import y' werkt in DAGs
ENV PYTHONPATH="/opt/airflow"

EXPOSE 8080

CMD ["standalone"]
