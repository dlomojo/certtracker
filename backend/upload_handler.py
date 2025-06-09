import json
import boto3
import uuid
import base64
from typing import Dict, Any
import os

# Initialize AWS services
s3_client = boto3.client('s3')

# Configuration
S3_BUCKET = os.environ.get('S3_BUCKET', 'certtracker-documents')
ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def lambda_handler(event, context):
    """Handle file upload to S3"""
    
    try:
        # Verify authentication
        user = verify_authentication(event)
        if not user:
            return create_response(401, {'error': 'Unauthorized'})
        
        # Parse the request
        method = event['httpMethod']
        
        if method == 'POST':
            return handle_file_upload(event, user)
        elif method == 'DELETE':
            return handle_file_delete(event, user)
        else:
            return create_response(405, {'error': 'Method not allowed'})
            
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return create_response(500, {'error': 'Upload failed'})

def handle_file_upload(event, user):
    """Handle file upload"""
    
    try:
        # Parse multipart form data or base64 content
        content_type = event.get('headers', {}).get('content-type', '')
        
        if 'multipart/form-data' in content_type:
            return handle_multipart_upload(event, user)
        else:
            return handle_base64_upload(event, user)
            
    except Exception as e:
        print(f"File upload error: {str(e)}")
        return create_response(500, {'error': 'File upload failed'})

def handle_base64_upload(event, user):
    """Handle base64 encoded file upload"""
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        file_content = body.get('file')
        filename = body.get('filename')
        content_type = body.get('contentType', 'application/octet-stream')
        
        if not file_content or not filename:
            return create_response(400, {'error': 'File content and filename are required'})
        
        # Decode base64 content
        file_data = base64.b64decode(file_content)
        
        # Validate file size
        if len(file_data) > MAX_FILE_SIZE:
            return create_response(400, {'error': 'File size exceeds 10MB limit'})
        
        # Generate unique filename
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            return create_response(400, {'error': 'File type not allowed'})
        
        unique_filename = f"{user['user_id']}/{uuid.uuid4()}{file_extension}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=unique_filename,
            Body=file_data,
            ContentType=content_type,
            Metadata={
                'userId': user['user_id'],
                'originalFilename': filename
            }
        )
        
        # Generate presigned URL for access
        file_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': unique_filename},
            ExpiresIn=3600 * 24 * 7  # 7 days
        )
        
        return create_response(200, {
            'url': file_url,
            'key': unique_filename,
            'filename': filename
        })
        
    except Exception as e:
        print(f"Base64 upload error: {str(e)}")
        return create_response(500, {'error': 'Upload failed'})

def handle_file_delete(event, user):
    """Handle file deletion"""
    
    try:
        query_params = event.get('queryStringParameters', {})
        file_key = query_params.get('key')
        
        if not file_key:
            return create_response(400, {'error': 'File key is required'})
        
        # Verify user owns the file
        if not file_key.startswith(f"{user['user_id']}/"):
            return create_response(403, {'error': 'Access denied'})
        
        # Delete from S3
        s3_client.delete_object(Bucket=S3_BUCKET, Key=file_key)
        
        return create_response(200, {'message': 'File deleted successfully'})
        
    except Exception as e:
        print(f"File delete error: {str(e)}")
        return create_response(500, {'error': 'Delete failed'})
