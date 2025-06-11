from dotenv import load_dotenv
load_dotenv()
import os
import argparse
import h5py
from pathlib import Path
import humanize
import boto3
from botocore.exceptions import NoCredentialsError
import h5py
import os
import zlib
import threading
from tqdm import tqdm

class TqdmUploadCallback:
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
        
        # Create progress bar
        self.pbar = tqdm(
            total=self._size,
            unit='B',
            unit_scale=True,
            desc=f"Uploading {os.path.basename(filename)}"
        )

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            self.pbar.update(bytes_amount)

    def close(self):
        self.pbar.close()

# Modified upload function
def upload_with_progress(file_path, s3_client, bucket, key, metadata):
    """Upload file to S3 with progress tracking"""
    callback = TqdmUploadCallback(file_path)

    try:
        with open(file_path, 'rb') as f:
            s3_client.upload_fileobj(
                f,
                bucket,
                key,
                ExtraArgs={
                    'Metadata': metadata,
                    'ContentType': 'application/x-hdf'
                },
                Callback=callback
            )
        
        # Clean up progress bar if using tqdm
        if hasattr(callback, 'close'):
            callback.close()
            
        print(f"\n✅ Upload completed: {key}")
        
    except Exception as e:
        if hasattr(callback, 'close'):
            callback.close()
        raise e

def generate_content_hash(file_path, hash_length=8):
    """Generate a short hash based on file contents
    
    Args:
        file_path: Path to the file
        hash_length: Length of hash to return (4-8 characters recommended)
    
    Returns:
        Short hash string
    """
    # Option 1: CRC32 (fast, good distribution, 8 hex chars max)
    if hash_length <= 8:
        with open(file_path, 'rb') as f:
            crc = 0
            while True:
                chunk = f.read(8192)  # Read in chunks for memory efficiency
                if not chunk:
                    break
                crc = zlib.crc32(chunk, crc)
        # Convert to unsigned and take first hash_length characters
        return f"{crc & 0xffffffff:08x}"[:hash_length]