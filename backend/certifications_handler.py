import json
import boto3
import uuid
from datetime import datetime
from typing import Dict, Any, List
import os

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Configuration
CERTIFICATIONS_TABLE = os.environ.get('CERTIFICATIONS_TABLE', 'certtracker-certifications')
S3_BUCKET = os.environ.get('S3_BUCKET', 'certtracker-documents')

certifications_table = dynamodb.Table(CERTIFICATIONS_TABLE)

def lambda_handler(event, context):
    """Main Lambda handler for certification endpoints"""
    
    try:
        # Parse the request
        method = event['httpMethod']
        path = event['path']
        path_parameters = event.get('pathParameters', {})
        body = json.loads(event.get('body', '{}'))
        
        # Verify authentication
        user = verify_authentication(event)
        if not user:
            return create_response(401, {'error': 'Unauthorized'})
        
        # Route to appropriate handler
        if path == '/certifications' and method == 'GET':
            return get_certifications(user['user_id'])
        elif path == '/certifications' and method == 'POST':
            return create_certification(user['user_id'], body)
        elif path.startswith('/certifications/') and method == 'GET':
            cert_id = path_parameters.get('id')
            return get_certification(user['user_id'], cert_id)
        elif path.startswith('/certifications/') and method == 'PUT':
            cert_id = path_parameters.get('id')
            return update_certification(user['user_id'], cert_id, body)
        elif path.startswith('/certifications/') and method == 'DELETE':
            cert_id = path_parameters.get('id')
            return delete_certification(user['user_id'], cert_id)
        else:
            return create_response(404, {'error': 'Endpoint not found'})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})

def verify_authentication(event) -> Dict[str, Any]:
    """Verify JWT token from Authorization header"""
    
    try:
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.replace('Bearer ', '')
        return verify_jwt_token(token)
        
    except Exception as e:
        print(f"Auth verification error: {str(e)}")
        return None

def get_certifications(user_id: str):
    """Get all certifications for a user"""
    
    try:
        response = certifications_table.scan(
            FilterExpression='userId = :user_id',
            ExpressionAttributeValues={':user_id': user_id}
        )
        
        certifications = response.get('Items', [])
        
        # Calculate status for each certification
        for cert in certifications:
            cert['status'] = calculate_status(cert['expiryDate'])
        
        return create_response(200, {
            'certifications': certifications,
            'count': len(certifications)
        })
        
    except Exception as e:
        print(f"Get certifications error: {str(e)}")
        return create_response(500, {'error': 'Failed to fetch certifications'})

def get_certification(user_id: str, cert_id: str):
    """Get a specific certification"""
    
    try:
        response = certifications_table.get_item(
            Key={'id': cert_id}
        )
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Certification not found'})
        
        cert = response['Item']
        
        # Verify ownership
        if cert['userId'] != user_id:
            return create_response(403, {'error': 'Access denied'})
        
        cert['status'] = calculate_status(cert['expiryDate'])
        
        return create_response(200, cert)
        
    except Exception as e:
        print(f"Get certification error: {str(e)}")
        return create_response(500, {'error': 'Failed to fetch certification'})

def create_certification(user_id: str, body: Dict[str, Any]):
    """Create a new certification"""
    
    try:
        # Validate required fields
        required_fields = ['name', 'provider', 'issueDate', 'expiryDate']
        for field in required_fields:
            if not body.get(field):
                return create_response(400, {'error': f'{field} is required'})
        
        # Create certification record
        cert_id = str(uuid.uuid4())
        certification = {
            'id': cert_id,
            'userId': user_id,
            'name': body['name'],
            'provider': body['provider'],
            'issueDate': body['issueDate'],
            'expiryDate': body['expiryDate'],
            'reminderDays': body.get('reminderDays', [90, 60, 30, 7]),
            'documentUrl': body.get('documentUrl'),
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat()
        }
        
        certification['status'] = calculate_status(certification['expiryDate'])
        
        certifications_table.put_item(Item=certification)
        
        return create_response(201, certification)
        
    except Exception as e:
        print(f"Create certification error: {str(e)}")
        return create_response(500, {'error': 'Failed to create certification'})

def update_certification(user_id: str, cert_id: str, body: Dict[str, Any]):
    """Update an existing certification"""
    
    try:
        # Get existing certification
        response = certifications_table.get_item(Key={'id': cert_id})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Certification not found'})
        
        cert = response['Item']
        
        # Verify ownership
        if cert['userId'] != user_id:
            return create_response(403, {'error': 'Access denied'})
        
        # Update fields
        updatable_fields = ['name', 'provider', 'issueDate', 'expiryDate', 'reminderDays', 'documentUrl']
        
        for field in updatable_fields:
            if field in body:
                cert[field] = body[field]
        
        cert['status'] = calculate_status(cert['expiryDate'])
        cert['updatedAt'] = datetime.utcnow().isoformat()
        
        certifications_table.put_item(Item=cert)
        
        return create_response(200, cert)
        
    except Exception as e:
        print(f"Update certification error: {str(e)}")
        return create_response(500, {'error': 'Failed to update certification'})

def delete_certification(user_id: str, cert_id: str):
    """Delete a certification"""
    
    try:
        # Get existing certification
        response = certifications_table.get_item(Key={'id': cert_id})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Certification not found'})
        
        cert = response['Item']
        
        # Verify ownership
        if cert['userId'] != user_id:
            return create_response(403, {'error': 'Access denied'})
        
        # Delete from DynamoDB
        certifications_table.delete_item(Key={'id': cert_id})
        
        return create_response(200, {'message': 'Certification deleted successfully'})
        
    except Exception as e:
        print(f"Delete certification error: {str(e)}")
        return create_response(500, {'error': 'Failed to delete certification'})

def calculate_status(expiry_date: str) -> str:
    """Calculate certification status based on expiry date"""
    
    try:
        from datetime import datetime, date
        
        expiry = datetime.fromisoformat(expiry_date.replace('Z', '')).date()
        today = date.today()
        days_until_expiry = (expiry - today).days
        
        if days_until_expiry < 0:
            return 'expired'
        elif days_until_expiry <= 30:
            return 'expiring'
        else:
            return 'active'
            
    except Exception:
        return 'unknown'