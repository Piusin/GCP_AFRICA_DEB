"""Load from API to GCS


Description: Ingests the data from a Public API into a gcp bucket.
"""

import os
import logging
from datetime import datetime
from airflow import DAG
from airflow.decorators import dag
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from google.cloud import storage
import pyarrow.csv as pv
from pathlib import Path
import requests 
import tempfile
import shutil

# constants
bucket = 'deb-gcp-bucket-pius'
gcp_conn = 'gcp_conn_id'
dataset_file_1= os.path.abspath("../datasets/movie_review.csv") # file name once downloaded
#credentials_file = Path("service_account.json")


def upload_file_func():
    hook = GCSHook(gcp_conn_id= gcp_conn)
    bucket_name = bucket
    object_name = dataset_file_1
    filename = Path(dataset_file_1)
    hook.upload(bucket_name, object_name, filename)
        
default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "depends_on_past": False,
    "retries": 0,
}

with DAG(
    dag_id="upload_to_gcs_from_local_dag",
    schedule_interval="@daily", # https://airflow.apache.org/docs/apache-airflow/1.10.1/scheduler.html
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    tags=['upload-gcs']
) as dag:
    
    
    upload_file = PythonOperator(task_id='upload_file', python_callable=upload_file_func)

    # Workflow for task direction
    upload_file