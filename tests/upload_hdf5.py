from dotenv import load_dotenv
load_dotenv()
import os
import argparse
import h5py
import numpy as np
import glob
from pathlib import Path
import pandas as pd
import humanize
from tqdm import tqdm
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import h5py
import io
import os
import json
from datetime import datetime
import tempfile
from werkzeug.utils import secure_filename

# Configuration
S3_BUCKET = os.environ.get('S3_BUCKET', 'your-s3-bucket-name')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
ALLOWED_EXTENSIONS = {'hdf5', 'h5'}

def extract_hdf5_metadata(file_path):
    """Extract metadata from HDF5 file"""
    metadata = {}
    try:
        with h5py.File(file_path, 'r') as f:
            # Try to get metadata from file attributes
            for key in ['dataset_name', 'sub-ID', 'pipeline', 'owner_name', 
                       'owner_email', 'trial_format', 'github_url', 'publication_url']:
                if key in f.attrs:
                    metadata[key] = f.attrs[key].decode('utf-8') if isinstance(f.attrs[key], bytes) else str(f.attrs[key])
                else:
                    metadata[key] = ""
    except Exception as e:
        print(f"Error reading HDF5 metadata: {e}")
        # Return empty metadata if file can't be read
        metadata = {
            'dataset_name': '',
            'subject_name': '',
            'pipeline': '',
            'owner_name': '',
            'owner_email': '',
            'trial_format': '',
            'github_url': '',
            'publication_url': ''
        }
    
    return metadata

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def main(args):
    file_path = os.path.join(args.save_root, "tests", "sub-01_hw.hdf5")
    print(file_path)

    # Initialize S3 client
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
    except NoCredentialsError:
        print("AWS credentials not found. Please configure your credentials.")
        s3_client = None

    """Upload HDF5 file to S3 with metadata"""
    if not s3_client:
        raise ValueError("error: S3 client not configured)")
    
    if not allowed_file(Path(file_path).name):
        raise ValueError(f"error: Only HDF5 files {ALLOWED_EXTENSIONS} are allowed")
    
    try:
        metadata = extract_hdf5_metadata(file_path=file_path)
        
        size_human_readable = humanize.naturalsize(os.path.getsize(file_path))
        metadata.update({"file_size": size_human_readable})

        # Secure filename
        filename = Path(file_path).name
        
        # Create unique filename if needed
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        
        # Upload to S3 with metadata
        s3_metadata = {k.replace('_', '-'): v for k, v in metadata.items() if v}
        
        with open(file_path, 'rb') as f:
            s3_client.upload_fileobj(
                f, 
                S3_BUCKET, 
                unique_filename,
                ExtraArgs={
                    'Metadata': s3_metadata,
                    'ContentType': 'application/x-hdf'
                }
            )
    except Exception as e:
        raise ValueError(f"{e}")

        
if __name__=='__main__':
    save_root_default = os.path.join(os.getenv("PROJECT_ROOT", "/default/path/to/project"), "mosaic-website") #use default if DATASETS_ROOT env variable is not set.

    parser = argparse.ArgumentParser()
    parser.add_argument("--save_root", type=str, default=save_root_default, help="Root path to scratch datasets folder.")

    args = parser.parse_args()
    
    main(args)