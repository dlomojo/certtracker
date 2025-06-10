import json
import boto3
import os
import uuid
import base64
import hmac
import hashlib
from datetime import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')

# Environment variables
USERS_TABLE = os.environ.get('USERS_TABLE', 'CertTracker-Users')
CERTIFICATIONS_TABLE = os.environ.get('CERTIFICATIONS_TABLE', 'CertTracker-Certifications')
USER_POOL_ID = os.environ.get('USER_POOL_ID')
CLIENT_ID = os.environ.get('USER_POOL_CLIENT_ID')

def handler(event, context):
    """Main API handler with production auth"""
    
    logger.info(f"Event: {json.dumps(event)}")
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    try:
        method = event.get('httpMethod')
        path = event.get('path', '/')
        
        if method == 'OPTIONS':
            return {'statusCode': 200, 'headers': headers, 'body': ''}
        
        if path.startswith('/auth'):
            return handle_auth(event, headers)
        elif path.startswith('/certifications'):
            return handle_certifications(event, headers)
        else:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Not found'})}
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def handle_auth(event, headers):
    """Handle authentication with Cognito"""
    
    method = event.get('httpMethod')
    body = json.loads(event.get('body', '{}'))
    
    if method == 'POST':
        if 'name' in body:  # Registration
            return register_user(body, headers)
        else:  # Login
            return login_user(body, headers)
    
    return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Invalid request'})}

def register_user(body, headers):
    """Register user with Cognito"""
    
    try:
        email = body['email']
        password = body['password']
        name = body['name']
        
        # Create user in Cognito
        response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'name', 'Value': name},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            TemporaryPassword=password,
            MessageAction='SUPPRESS'
        )
        
        # Set permanent password
        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=email,
            Password=password,
            Permanent=True
        )
        
        # Store user profile
        user_id = response['User']['Username']
        users_table = dynamodb.Table(USERS_TABLE)
        
        users_table.put_item(Item={
            'userId': user_id,
            'email': email,
            'name': name,
            'createdAt': datetime.utcnow().isoformat()
        })
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': 'User registered successfully',
                'user': {'id': user_id, 'email': email, 'name': name}
            })
        }
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def login_user(body, headers):
    """Login with Cognito and return JWT tokens"""
    
    try:
        email = body['email']
        password = body['password']
        
        # Build auth parameters
        auth_params = {
            'USERNAME': email,
            'PASSWORD': password
        }
        
        # Only add SECRET_HASH if client secret exists
        client_secret = os.environ.get('CLIENT_SECRET')
        if client_secret:
            auth_params['SECRET_HASH'] = calculate_secret_hash(email)
        
        # Authenticate with Cognito
        response = cognito.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters=auth_params
        )
        
        # Get user details
        user_response = cognito.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=email
        )
        
        # Extract user attributes
        user_attrs = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Login successful',
                'user': {
                    'id': user_response['Username'],
                    'email': user_attrs.get('email'),
                    'name': user_attrs.get('name')
                },
                'tokens': {
                    'AccessToken': response['AuthenticationResult']['AccessToken'],
                    'IdToken': response['AuthenticationResult']['IdToken'],
                    'RefreshToken': response['AuthenticationResult']['RefreshToken']
                }
            })
        }
        
    except cognito.exceptions.NotAuthorizedException:
        return {'statusCode': 401, 'headers': headers, 'body': json.dumps({'error': 'Invalid credentials'})}
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def calculate_secret_hash(username):
    """Calculate secret hash for Cognito client"""
    
    client_secret = os.environ.get('CLIENT_SECRET', '')
    if not client_secret:
        return None
        
    message = username + CLIENT_ID
    key = client_secret.encode('utf-8')
    message = message.encode('utf-8')
    
    dig = hmac.new(key, message, hashlib.sha256).digest()
    return base64.b64encode(dig).decode()

def handle_certifications(event, headers):
    """Handle certification endpoints - protected by Cognito"""
    
    # Debug: Log the entire event to see structure
    logger.info(f"Full event: {json.dumps(event)}")
    
    # Try different paths for user info
    user_id = None
    request_context = event.get('requestContext', {})
    
    # Method 1: Standard Cognito authorizer
    if 'authorizer' in request_context:
        claims = request_context['authorizer'].get('claims', {})
        user_id = claims.get('sub') or claims.get('cognito:username')
        logger.info(f"Method 1 - Claims: {claims}")
    
    # Method 2: Direct in requestContext
    if not user_id:
        user_id = request_context.get('identity', {}).get('cognitoIdentityId')
        logger.info(f"Method 2 - Identity: {request_context.get('identity')}")
    
    logger.info(f"Extracted user_id: {user_id}")
    
    if not user_id:
        return {
            'statusCode': 401, 
            'headers': headers, 
            'body': json.dumps({
                'error': 'Unauthorized', 
                'debug': {
                    'requestContext': request_context,
                    'hasAuthorizer': 'authorizer' in request_context
                }
            })
        }
    
    method = event.get('httpMethod')
    
    if method == 'GET':
        return get_certifications(user_id, headers)
    elif method == 'POST':
        return create_certification(event, user_id, headers)
    
    return {'statusCode': 405, 'headers': headers, 'body': json.dumps({'error': 'Method not allowed'})}

def get_certifications(user_id, headers):
    """Get user's certifications from DynamoDB"""
    
    try:
        certs_table = dynamodb.Table(CERTIFICATIONS_TABLE)
        
        response = certs_table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        
        certifications = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'certifications': certifications,
                'count': len(certifications)
            })
        }
        
    except Exception as e:
        logger.error(f"Get certifications error: {str(e)}")
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def create_certification(event, user_id, headers):
    """Create new certification"""
    
    try:
        body = json.loads(event.get('body', '{}'))
        cert_id = str(uuid.uuid4())
        
        certs_table = dynamodb.Table(CERTIFICATIONS_TABLE)
        
        certification = {
            'userId': user_id,
            'certId': cert_id,
            'name': body['name'],
            'provider': body['provider'],
            'issueDate': body['issueDate'],
            'expiryDate': body['expiryDate'],
            'status': 'active',
            'reminderDays': body.get('reminderDays', [90, 60, 30, 7]),
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat()
        }
        
        certs_table.put_item(Item=certification)
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'id': cert_id,
                'message': 'Certification created successfully',
                'certification': certification
            })
        }
        
    except Exception as e:
        logger.error(f"Create certification error: {str(e)}")
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}