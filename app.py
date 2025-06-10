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

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
CORS(app)  # Enable CORS for frontend

# Configuration
S3_BUCKET = os.environ.get('S3_BUCKET', 'your-s3-bucket-name')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'hdf5', 'h5'}

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
        # Get metadata from form
        metadata = {
            'dataset_name': request.form.get('datasetName', ''),
            'subjectID': request.form.get('subjectName', ''),
            'preprocessing_pipeline': request.form.get('preprocessingPipeline', ''),
            'owner_name': request.form.get('ownerName', ''),
            'owner_email': request.form.get('ownerEmail', ''),
            'beta_pipeline': request.form.get('betaPipeline', ''),
            'github_url': request.form.get('githubUrl', ''),
            'publication_url': request.form.get('publicationUrl', '')
        }
        
        # Secure filename
        filename = secure_filename(file.filename)
        
        # Create unique filename if needed
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        
        # Save file temporarily
        temp_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(temp_path)
        
        # Upload to S3 with metadata
        s3_metadata = {k.replace('_', '-'): v for k, v in metadata.items() if v}
        
        with open(temp_path, 'rb') as f:
            s3_client.upload_fileobj(
                f, 
                S3_BUCKET, 
                unique_filename,
                ExtraArgs={
                    'Metadata': s3_metadata,
                    'ContentType': 'application/x-hdf'
                }
            )
        
        # Clean up temporary file
        os.remove(temp_path)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'filename': unique_filename,
            'metadata': metadata
        })
    
    except ClientError as e:
        return jsonify({'error': f'S3 upload error: {e.response["Error"]["Code"]}'}), 500
    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
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
    
    app.run(debug=True, host='0.0.0.0', port=5000)