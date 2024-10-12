from flask import Flask, request, jsonify, send_from_directory, Response
import os
import boto3
import csv
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import time

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join('static', filename)
        file.save(file_path)

        s3_client = boto3.client('s3')
        bucket_name = os.getenv('S3_BUCKET_NAME')
        s3_key = f"input/{filename}"
        s3_client.upload_file(file_path, bucket_name, s3_key)

        textract = boto3.client('textract')
        response = textract.analyze_document(
            Document={'S3Object': {'Bucket': bucket_name, 'Name': s3_key}},
            FeatureTypes=['TABLES', 'FORMS']
        )

        text_blocks = [block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE']
        
        csv_file = f'static/{filename.split(".")[0]}.csv'
        with open(csv_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Text'])
            for text in text_blocks:
                writer.writerow([text])
        
        csv_s3_key = f"input/{filename.split('.')[0]}.csv"
        s3_client.upload_file(csv_file, bucket_name, csv_s3_key)

        glue_client = boto3.client('glue')
        job_name = os.getenv('GLUE_JOB_NAME')
        response = glue_client.start_job_run(
            JobName=job_name,
            Arguments={
                '--SOURCE_BUCKET': bucket_name,
                '--SOURCE_KEY': csv_s3_key,
                '--TARGET_BUCKET': bucket_name,
                '--TARGET_KEY': f"output/{filename.split('.')[0]}_cleaned.csv"
            }
        )
        job_run_id = response['JobRunId']

        # Check the job status
        while True:
            status_response = glue_client.get_job_run(JobName=job_name, RunId=job_run_id)
            status = status_response['JobRun']['JobRunState']
            if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
                break
            time.sleep(10)

        if status == 'SUCCEEDED':
            output_s3_key = f"output/{filename.split('.')[0]}_cleaned.csv"
            app.logger.info(f"Glue job succeeded. Output S3 Key: {output_s3_key}")
            return jsonify({'message': 'File processed successfully', 's3_key': output_s3_key})
        else:
            app.logger.error(f"Glue job failed with status: {status}")
            return jsonify({'error': 'Glue job failed'}), 500

    app.logger.error("No file uploaded")
    return jsonify({"error": "No file uploaded"}), 400

@app.route('/fetch_cleaned_file', methods=['GET'])
def fetch_cleaned_file():
    s3_key = request.args.get('s3_key')
    if not s3_key:
        return jsonify({'error': 'Missing s3_key parameter'}), 400

    bucket_name = os.getenv('S3_BUCKET_NAME')
    s3_client = boto3.client('s3')
    try:
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        file_content = file_obj['Body'].read().decode('utf-8')
        return Response(file_content, mimetype='text/csv')
    except Exception as e:
        app.logger.error(f"Error fetching file from S3: {e}")
        return jsonify({'error': 'Error fetching file from S3'}), 500

if __name__ == '__main__':
    app.run(debug=True)
