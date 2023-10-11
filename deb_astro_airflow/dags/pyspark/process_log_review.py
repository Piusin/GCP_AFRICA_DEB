from pyspark.sql import SparkSession
from pyspark.sql.types import IntegerType, DateType
from datetime import datetime

# bucket = "useranalytics-pipeline-bucket"
# staging_bucket = "useranalytics-pipeline-bucket-staging"
# key = "data/log_reviews.csv"
GCP_BUCKET = "deb-gcp-bucket-pius"
GCP_STAGING_BUCKET = 'deb-gcp-bucket-pius'
GCS_KEY_NAME = "Bronze/log_review.csv"

file = f"gs://{GCP_BUCKET}/{GCS_KEY_NAME}"

spark = SparkSession.builder.appName("ProcessLogReview").getOrCreate()
df = spark.read.csv(file, inferSchema=True, header=True, sep=",")

ddf = df.selectExpr(
    "id_review as log_id",
    "xpath_string(log, '/reviewlog/log/logDate') as log_date",
    "xpath_string(log, '/reviewlog/log/device') as device",
    "xpath_string(log, '/reviewlog/log/location') as location",
    "xpath_string(log, '/reviewlog/log/os') as os",
    "xpath_string(log, '/reviewlog/log/ipAddress') as ip_address",
    "xpath_string(log, '/reviewlog/log/phoneNumber') as phone_number",
)

date = datetime.now().strftime("%Y/%m/%d")
ddf = ddf.withColumn("log_date", ddf["log_date"].cast(DateType()))
ddf.printSchema()
ddf.write.parquet(f"gs://{GCP_STAGING_BUCKET}/log_review/{date}", mode="overwrite")