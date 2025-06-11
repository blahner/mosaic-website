from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import h5py
import io
import os
import json
import humanize
from datetime import datetime
import tempfile
from werkzeug.utils import secure_filename
from pathlib import Path

#local
from utils.helpers import upload_with_progress, generate_content_hash

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
CORS(app)  # Enable CORS for frontend

# Configuration
S3_BUCKET = os.environ.get('S3_BUCKET', 'your-s3-bucket-name')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'hdf5', 'h5'}
UPLOAD_SIZE_LIMIT=30 #GB

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize S3 client
try:
    s3_client = boto3.client('s3', region_name=AWS_REGION)
except NoCredentialsError:
    print("AWS credentials not found. Please configure your credentials.")
    s3_client = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_hdf5_metadata(file_path):
    """Extract metadata from HDF5 file"""
    metadata = {}
    try:
        with h5py.File(file_path, 'r') as f:
            # Try to get metadata from file attributes
            for key in ['dataset_name', 'subjectID', 'preprocessing_pipeline', 'owner_name', 
                       'owner_email', 'beta_pipeline', 'github_url', 'publication_url']:
                if key in f.attrs:
                    metadata[key] = f.attrs[key].decode('utf-8') if isinstance(f.attrs[key], bytes) else str(f.attrs[key])
                else:
                    metadata[key] = ""
    except Exception as e:
        print(f"Error reading HDF5 metadata: {e}")
        # Return empty metadata if file can't be read
        metadata = {
            'dataset_name': '',
            'subjectID': '',
            'preprocessing_pipeline': '',
            'owner_name': '',
            'owner_email': '',
            'beta_pipeline': '',
            'github_url': '',
            'publication_url': ''
        }
    
    return metadata

def get_s3_object_metadata(key):
    """Get metadata from S3 object tags and attributes"""
    try:
        # Get object metadata
        response = s3_client.head_object(Bucket=S3_BUCKET, Key=key)
        
        # Get custom metadata from object metadata
        metadata = response.get('Metadata', {})
        
        # Ensure all required fields exist
        required_fields = ['dataset_name', 'subjectID', 'preprocessing_pipeline', 'owner_name', 
                          'owner_email', 'beta_pipeline', 'github_url', 'publication_url']
        for field in required_fields:
            if field not in metadata:
                metadata[field] = ""
        
        return metadata
    except Exception as e:
        print(f"Error getting metadata for {key}: {e}")
        return {}

def list_s3_crc32():
    """
    Get the crc32 hashes for each object in the s3 bucket and return as dict,
    not jsonify for flask app. Otherwise similar to function 'list_s3_files()'.
    """
    """List all HDF5 files in S3 bucket with metadata"""
    if not s3_client:
        return {'error': 'S3 client not configured'}
    
    try:
        # List objects in bucket
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET)
        
        if 'Contents' not in response:
            return {}
        
        files_data = {}
        for obj in response['Contents']:
            key = obj['Key']
            
            # Only process HDF5 files
            if not (key.endswith('.hdf5') or key.endswith('.h5')):
                continue
            
            # Get metadata for this file
            metadata = get_s3_object_metadata(key)
            files_data.update({key: metadata.get("crc32_hash", "")})
        
        return files_data
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            return {'error': 'S3 bucket not found'}
        else:
            return {'error': f'S3 error: {error_code}'}
    except Exception as e:
        return {'error': str(e)}

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/upload')
def upload():
    """Upload page"""
    return render_template('upload.html')

@app.route('/download')
def download():
    """download page"""
    return render_template('download.html')

@app.route('/faq')
def faq():
    """faq page"""
    return render_template('faq.html')

@app.route('/api/s3/files', methods=['GET'])
def list_s3_files():
    """List all HDF5 files in S3 bucket with metadata"""
    if not s3_client:
        return jsonify({'error': 'S3 client not configured'}), 500
    
    try:
        # List objects in bucket
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET)
        
        if 'Contents' not in response:
            return jsonify([])
        
        files_data = []
        for obj in response['Contents']:
            key = obj['Key']
            
            # Only process HDF5 files
            if not (key.endswith('.hdf5') or key.endswith('.h5')):
                continue
            
            # Get metadata for this file
            metadata = get_s3_object_metadata(key)
            
            file_data = {
                'fileId': key,
                'datasetName': metadata.get('dataset_name', ''),
                'subjectName': metadata.get('subjectID', ''),
                'preprocessingPipeline': metadata.get('preprocessing_pipeline', ''),
                'ownerName': metadata.get('owner_name', ''),
                'ownerEmail': metadata.get('owner_email', ''),
                'betaPipeline': metadata.get('beta_pipeline', ''),
                'githubUrl': metadata.get('github_url', ''),
                'publicationUrl': metadata.get('publication_url', ''),
                'lastModified': obj['LastModified'].isoformat(),
                'size': humanize.naturalsize(obj['Size'], binary=True)
            }
            
            files_data.append(file_data)
        
        return jsonify(files_data)
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            return jsonify({'error': 'S3 bucket not found'}), 404
        else:
            return jsonify({'error': f'S3 error: {error_code}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/s3/upload', methods=['POST'])
def upload_to_s3():
    """Upload HDF5 file to S3 with metadata"""
    if not s3_client:
        return jsonify({'error': 'S3 client not configured'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only HDF5 files (.hdf5, .h5) are allowed'}), 400
    
    try:
        size_human_readable = humanize.naturalsize(os.path.getsize(file))
        if size_human_readable > UPLOAD_SIZE_LIMIT:
            return jsonify({'error': f"Desired file upload size was {size_human_readable} and the max is {UPLOAD_SIZE_LIMIT}. Contact us if you truly have a file this large to upload."})
        metadata = extract_hdf5_metadata(file)
        
        # Secure filename
        filename = secure_filename(file.filename)
        metadata.update({"file_size": size_human_readable})
        
        #use crc32 to hash hdf5 file. any change in file creates new hash
        #hash just intended to ensure files are same or different
        crc32_hash = generate_content_hash(file)

        #get other s3 object crc32 hash
        existing_objects = list_s3_crc32()
        existing_hashes = set(existing_objects.values())
        if crc32_hash in existing_hashes:
            return jsonify({'error': 'This file has already been uploaded.'})

        filename = Path(file).name
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_crc32-{crc32_hash}{ext}"

        metadata.update({"crc32_hash": crc32_hash})

        upload_with_progress(
            file_path=file,
            s3_client=s3_client,
            bucket=S3_BUCKET,
            key=unique_filename,
            metadata=metadata
        )
        
        return jsonify({
            'message': 'File uploaded successfully',
            'filename': unique_filename,
            'metadata': metadata
        })
    
    except ClientError as e:
        return jsonify({'error': f'S3 upload error: {e.response["Error"]["Code"]}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/s3/download/<path:filename>', methods=['GET'])
def download_from_s3(filename):
    """Generate presigned URL for downloading file from S3"""
    if not s3_client:
        return jsonify({'error': 'S3 client not configured'}), 500
    
    try:
        # Generate presigned URL (valid for 1 hour)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': filename},
            ExpiresIn=3600
        )
        return jsonify({'download_url': url})
    except ClientError as e:
        return jsonify({'error': f'S3 error: {e.response["Error"]["Code"]}'}), 500

@app.route('/api/s3/bucket/info', methods=['GET'])
def get_bucket_info():
    """Get S3 bucket information"""
    if not s3_client:
        return jsonify({'error': 'S3 client not configured'}), 500
    
    try:
        # Check if bucket exists and is accessible
        s3_client.head_bucket(Bucket=S3_BUCKET)
        
        # Get bucket location
        location_response = s3_client.get_bucket_location(Bucket=S3_BUCKET)
        location = location_response.get('LocationConstraint', 'us-east-1')
        
        return jsonify({
            'bucket_name': S3_BUCKET,
            'region': location,
            'accessible': True
        })
    except ClientError as e:
        return jsonify({
            'bucket_name': S3_BUCKET,
            'accessible': False,
            'error': e.response['Error']['Code']
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Check environment
    if not S3_BUCKET or S3_BUCKET == 'your-s3-bucket-name':
        print("Warning: Please set the S3_BUCKET environment variable")
    
    print(f"Starting Flask app...")
    print(f"S3 Bucket: {S3_BUCKET}")
    print(f"AWS Region: {AWS_REGION}")
    
    app.run(port=5001, debug=True)