import os

import psycopg


def connect():
    """Open a new Postgres connection from environment variables.

    In Kubernetes, DB_HOST comes from a ConfigMap and DB_PASSWORD from a Secret.
    """
    return psycopg.connect(
        host=os.getenv("DB_HOST", "postgres"),
        dbname=os.getenv("DB_NAME", "quickbite"),
        user=os.getenv("DB_USER", "quickbite"),
        password=os.getenv("DB_PASSWORD", "quickbite"),
        connect_timeout=2,
    )
