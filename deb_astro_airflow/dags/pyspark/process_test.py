from pyspark.sql import SparkSession
from pyspark.ml.feature import Tokenizer

bucket = 'deb-gcp-bucket-pius'
#staging_bucket = 'useranalytics-pipeline-bucket-staging'
key = 'Bronze/movie_review.csv'
local_key = '../data/movie_review.csv'

# Create a Spark session
spark = SparkSession.builder.appName("ProcessMovieReview").getOrCreate()

#datax = spark.read.csv(f'gs://{bucket}/{key}', inferSchema=True, header=True, sep=',')
datax = spark.read.csv(local_key, inferSchema=True, header=True, sep=',')

# Create a DataFrame
df = spark.createDataFrame(datax, ["cid", "review_str"])

# Instantiate the Tokenizer
tokenizer = Tokenizer(inputCol="review_str", outputCol="review_token")

# Tokenize the 'review_str' column and add the result to a new column 'review_token'
tokenized_df = tokenizer.transform(df)

# Show the result
tokenized_df.select("cid", "review_token").show(truncate=False)

# Stop the Spark session
spark.stop()
