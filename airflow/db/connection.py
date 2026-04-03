import os
import psycopg2
from urllib.parse import urlparse, unquote


def get_connection() -> psycopg2.extensions.connection:
    """
    Bouw een psycopg2-verbinding op via DATABASE_URL (uit Azure Key Vault / ACI env).
    SSL is verplicht voor Azure PostgreSQL.
    """
    raw = os.environ.get("DATABASE_URL", "")
    if not raw:
        raise EnvironmentError("DATABASE_URL omgevingsvariabele is niet ingesteld.")

    # Azure Key Vault references zijn al opgelost door ACI via env inject
    p = urlparse(raw)
    # urlparse decodeert geen percent-encoding in username/password — dit doen we zelf
    sslmode = "disable" if p.hostname in ("localhost", "127.0.0.1") else "require"
    return psycopg2.connect(
        dbname=p.path.lstrip("/"),
        user=unquote(p.username or ""),
        password=unquote(p.password or ""),
        host=p.hostname,
        port=p.port or 5432,
        sslmode=sslmode,
    )
