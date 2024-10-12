import sys
import boto3

def main():
    args = sys.argv[1:]
    source_bucket = None
    source_key = None
    target_bucket = None
    target_key = None

    for arg in args:
        if arg.startswith('--SOURCE_BUCKET='):
            source_bucket = arg.split('=')[1]
        elif arg.startswith('--SOURCE_KEY='):
            source_key = arg.split('=')[1]
        elif arg.startswith('--TARGET_BUCKET='):
            target_bucket = arg.split('=')[1]
        elif arg.startswith('--TARGET_KEY='):
            target_key = arg.split('=')[1]

    if not source_bucket or not source_key or not target_bucket or not target_key:
        raise ValueError('Missing required arguments: --SOURCE_BUCKET, --SOURCE_KEY, --TARGET_BUCKET, --TARGET_KEY')

    s3 = boto3.client('s3')

    download_path = f'/tmp/{source_key.split("/")[-1]}'
    s3.download_file(source_bucket, source_key, download_path)

    processed_content = process_file(download_path)

    upload_path = f'/tmp/{target_key.split("/")[-1]}'
    with open(upload_path, 'w') as f:
        f.write(processed_content)

    s3.upload_file(upload_path, target_bucket, target_key)

def process_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    processed_content = content.upper()  
    return processed_content

if __name__ == '__main__':
    main()
