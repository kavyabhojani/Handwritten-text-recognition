import re
import sys
import boto3
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, lower, regexp_replace, trim

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'SOURCE_BUCKET', 'SOURCE_KEY', 'TARGET_BUCKET', 'TARGET_KEY'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Load data from S3
s3_path = f"s3://{args['SOURCE_BUCKET']}/{args['SOURCE_KEY']}"
df = spark.read.option("header", "true").csv(s3_path)

# Define cleaning functions
def clean_text(column):
    # Convert to lowercase
    cleaned = lower(column)
    # Remove special characters
    cleaned = regexp_replace(cleaned, r'[^a-zA-Z0-9\s]', '')
    # Normalize whitespace
    cleaned = regexp_replace(cleaned, r'\s+', ' ')
    # Trim leading and trailing whitespace
    cleaned = trim(cleaned)
    return cleaned.alias('cleaned_text')

# Apply cleaning functions
df_cleaned = df.withColumn("cleaned_text", clean_text(col("Text")))

# Save cleaned data back to S3
temp_output_path = f"s3://{args['TARGET_BUCKET']}/temp_{args['TARGET_KEY']}"
df_cleaned.write.option("header", "true").mode('overwrite').csv(temp_output_path)

# Move the part file to the correct target location
s3 = boto3.client('s3')

bucket = args['TARGET_BUCKET']
temp_key_prefix = f"temp_{args['TARGET_KEY']}"
final_key = args['TARGET_KEY']

# List objects in the temporary directory
objects = s3.list_objects_v2(Bucket=bucket, Prefix=temp_key_prefix)
for obj in objects.get('Contents', []):
    temp_key = obj['Key']
    if temp_key.endswith('.csv'):
        # Move the part file to the final destination
        copy_source = {'Bucket': bucket, 'Key': temp_key}
        s3.copy_object(CopySource=copy_source, Bucket=bucket, Key=final_key)
        s3.delete_object(Bucket=bucket, Key=temp_key)

# Clean up the temporary directory
for obj in objects.get('Contents', []):
    s3.delete_object(Bucket=bucket, Key=obj['Key'])

job.commit()
