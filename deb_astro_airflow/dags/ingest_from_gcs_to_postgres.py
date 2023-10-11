"""Database Ingestion Workflow

Based on: https://github.com/enroliv/adios/blob/main/dags/ingest_to_db_from_gcs.py

Description: Ingests the data from a GCS bucket into a postgres table.
"""

from airflow.models import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.sql import BranchSQLOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
import os
import pandas as pd
import re

# General constants
DAG_ID = "ingestion_workflow_gcp_to_postgres"
STABILITY_STATE = "under_review"
CLOUD_PROVIDER = "gcp"

# GCP constants
GCP_CONN_ID = 'gcp_conn_id'
GCS_BUCKET_NAME = "deb-gcp-bucket-pius"
GCS_KEY_NAME = "Bronze/user_purchase.csv"

# Postgres constants
POSTGRES_CONN_ID = "postgres_conn_id"
POSTGRES_TABLE_NAME = "user_purchase"

# def standardize_stockcode(stockcode):
#     # Remove non-alphanumeric characters using regular expression
#     standardized_stockcode = re.sub(r'[^A-Za-z0-9]', '', stockcode)
#     # Convert to uppercase
#     standardized_stockcode = standardized_stockcode.upper()
#     return standardized_stockcode



def ingest_data_from_gcs(
    gcs_bucket: str,
    gcs_object: str,
    postgres_table: str,
    gcp_conn_id: str = 'gcp_conn_id',
    postgres_conn_id: str = "postgres_conn_id",
):
    """Ingest data from an GCS location into a postgres table.

    Args:
        gcs_bucket (str): Name of the bucket.
        gcs_object (str): Name of the object.
        postgres_table (str): Name of the postgres table.
        gcp_conn_id (str): Name of the Google Cloud connection ID.
        postgres_conn_id (str): Name of the postgres connection ID.
    """
    import tempfile

    gcs_hook = GCSHook(gcp_conn_id=gcp_conn_id)
    psql_hook = PostgresHook(postgres_conn_id)

    with tempfile.NamedTemporaryFile() as tmp:
        gcs_hook.download(
            bucket_name=gcs_bucket, object_name=gcs_object, filename=tmp.name
        )

        # Define the schema of your PostgreSQL table
        schema = [
            "invoiceNo",
            "stockCode",
            "description",
            "quantity",
            "invoiceDate",
            "unitPrice",
            "customerID",
            "country"
        ]

        # Read the data from the GCS file and insert it into the PostgreSQL table
        with open(tmp.name, "r") as file:
            lines = file.readlines()
            for line in lines:
                data = line.strip().split(",")  # Split the line based on the delimiter (comma)
                if len(data) == len(schema) and data[0] != "InvoiceNo":
                    # Construct an INSERT statement with placeholders
                    insert_sql = f"INSERT INTO {postgres_table} ({', '.join(schema)}) VALUES ({', '.join(['%s' for _ in schema])})"
                    psql_hook.run(insert_sql, parameters=data)
                else:
                    pass

        #psql_hook.bulk_load(table=postgres_table, tmp_file=tmp.name)
    
   

with DAG(
    dag_id=DAG_ID,
    schedule_interval="@once",
    start_date=days_ago(1),
    tags=[CLOUD_PROVIDER, STABILITY_STATE],
) as dag:
    start_workflow = DummyOperator(task_id="start_workflow")

    verify_key_existence = GCSObjectExistenceSensor(
        task_id="verify_key_existence",
        google_cloud_conn_id=GCP_CONN_ID,
        bucket=GCS_BUCKET_NAME,
        object=GCS_KEY_NAME,
    )

    create_table_entity = PostgresOperator(
        task_id="create_table_entity",
        postgres_conn_id=POSTGRES_CONN_ID,
        sql=f"""
            CREATE TABLE IF NOT EXISTS {POSTGRES_TABLE_NAME} (
                    invoiceNo varchar(20),
                    stockCode varchar(20),
                    description varchar(1000),
                    quantity INT,
                    invoiceDate timestamp,
                    unitPrice numeric(8,3),
                    customerID varchar(20),
                    country varchar(20)
            )
        """,
    )

    clear_table = PostgresOperator(
        task_id="clear_table",
        postgres_conn_id=POSTGRES_CONN_ID,
        sql=f"DELETE FROM {POSTGRES_TABLE_NAME}",
    )
    continue_process = DummyOperator(task_id="continue_process")

    ingest_data = PythonOperator(
        task_id="ingest_data",
        python_callable=ingest_data_from_gcs,
        op_kwargs={
            "gcp_conn_id": GCP_CONN_ID,
            "postgres_conn_id": POSTGRES_CONN_ID,
            "gcs_bucket": GCS_BUCKET_NAME,
            "gcs_object": GCS_KEY_NAME,
            "postgres_table": POSTGRES_TABLE_NAME,
        },
        trigger_rule=TriggerRule.ONE_SUCCESS,
    )

    validate_data = BranchSQLOperator(
        task_id="validate_data",
        conn_id=POSTGRES_CONN_ID,
        sql=f"SELECT COUNT(*) AS total_rows FROM {POSTGRES_TABLE_NAME}",
        follow_task_ids_if_false=[continue_process.task_id],
        follow_task_ids_if_true=[clear_table.task_id],
    )

    end_workflow = DummyOperator(task_id="end_workflow")

    (
        start_workflow
        >> verify_key_existence
        >> create_table_entity
        >> validate_data
    )
    validate_data >> [clear_table, continue_process] >> ingest_data
    ingest_data >> end_workflow

    dag.doc_md = __doc__