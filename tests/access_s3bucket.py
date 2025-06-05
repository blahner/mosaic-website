from dotenv import load_dotenv
load_dotenv()
import os
import subprocess

def list_s3bucket_contents():
    cmd = ['aws','s3', 'ls', f"s3://{os.getenv('S3_BUCKET', 'your-bucket-name')}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result)
    print(result.stdout)
    print(result.stderr)
    print(result.returncode)

list_s3bucket_contents()