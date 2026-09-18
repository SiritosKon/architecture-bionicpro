import os
from datetime import datetime, timedelta

import clickhouse_connect
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator

CRM_DSN = os.getenv(
    "CRM_DSN", "host=crm_db port=5432 dbname=crm user=crm_user password=crm_password"
)
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "reports")

AGGREGATE_SQL = """
    SELECT
        t.user_id,
        date_trunc('day', t.event_ts)::date              AS period,
        c.full_name,
        c.prosthesis_model,
        count(*)                                          AS total_events,
        avg(t.response_time_ms)                           AS avg_response_ms,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY t.response_time_ms) AS p95_response_ms,
        count(t.movement)                                 AS movements_count,
        avg(t.battery_pct)                                AS avg_battery
    FROM telemetry t
    JOIN clients c ON c.user_id = t.user_id
    GROUP BY t.user_id, period, c.full_name, c.prosthesis_model
"""


def build_mart(**_):
    conn = psycopg2.connect(CRM_DSN)
    try:
        with conn.cursor() as cur:
            cur.execute(AGGREGATE_SQL)
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return

    ch = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT, database=CLICKHOUSE_DB
    )
    ch.insert(
        "user_reports",
        [list(r) for r in rows],
        column_names=[
            "user_id", "period", "full_name", "prosthesis_model",
            "total_events", "avg_response_ms", "p95_response_ms",
            "movements_count", "avg_battery",
        ],
    )


default_args = {
    "owner": "bionicpro",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="crm_to_olap_reports",
    default_args=default_args,
    description="ETL: CRM telemetry -> ClickHouse reporting mart",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["bionicpro", "reports"],
) as dag:
    PythonOperator(task_id="build_user_reports_mart", python_callable=build_mart)
