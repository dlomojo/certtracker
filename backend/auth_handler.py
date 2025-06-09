import json
import boto3
import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
import os
from typing import Dict, Any

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
cognito_client = boto3.client('cognito-idp')

# Configuration
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID')
CLIENT_ID = os.environ.get('COGNITO_CLIENT_ID')
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-jwt-secret-change-this')
USERS_TABLE = os.environ.get('USERS_TABLE', 'certtracker-users')

users_table = dynamodb.Table(USERS_TABLE)

def lambda_handler(event, context):
    """Main Lambda handler for authentication endpoints"""
    
    try:
        # Parse the request
        method = event['httpMethod']
        path = event['path']
        body = json.loads(event.get('body', '{}'))
        
        # Route to appropriate handler
        if path == '/auth/login' and method == 'POST':
            return handle_login(body)
        elif path == '/auth/register' and method == 'POST':
            return handle_register(body)
        elif path == '/auth/logout' and method == 'POST':
            return handle_logout(event)
        else:
            return create_response(404, {'error': 'Endpoint not found'})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})

def handle_login(body: Dict[str, Any]):
    """Handle user login"""
    
    email = body.get('email')
    password = body.get('password')
    
    if not email or not password:
        return create_response(400, {'error': 'Email and password are required'})
    
    try:
        # Get user from DynamoDB
        response = users_table.get_item(Key={'email': email})
        
        if 'Item' not in response:
            return create_response(401, {'error': 'Invalid credentials'})
        
        user = response['Item']
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return create_response(401, {'error': 'Invalid credentials'})
        
        # Generate JWT token
        token = generate_jwt_token(user)
        
        # Return user data (without password)
        user_data = {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'createdAt': user.get('createdAt')
        }
        
        return create_response(200, {
            'user': user_data,
            'token': token
        })
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return create_response(500, {'error': 'Login failed'})

def handle_register(body: Dict[str, Any]):
    """Handle user registration"""
    
    email = body.get('email')
    password = body.get('password')
    name = body.get('name')
    
    if not email or not password or not name:
        return create_response(400, {'error': 'Email, password, and name are required'})
    
    try:
        # Check if user already exists
        response = users_table.get_item(Key={'email': email})
        
        if 'Item' in response:
            return create_response(409, {'error': 'User already exists'})
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user
        user_id = str(uuid.uuid4())
        user_data = {
            'id': user_id,
            'email': email,
            'name': name,
            'password_hash': password_hash,
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat()
        }
        
        users_table.put_item(Item=user_data)
        
        # Generate JWT token
        token = generate_jwt_token(user_data)
        
        # Return user data (without password)
        response_user = {
            'id': user_data['id'],
            'email': user_data['email'],
            'name': user_data['name'],
            'createdAt': user_data['createdAt']
        }
        
        return create_response(201, {
            'user': response_user,
            'token': token
        })
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return create_response(500, {'error': 'Registration failed'})

def handle_logout(event):
    """Handle user logout"""
    # In a JWT-based system, logout is typically handled client-side
    # by removing the token from storage
    return create_response(200, {'message': 'Logged out successfully'})

def generate_jwt_token(user: Dict[str, Any]) -> str:
    """Generate JWT token for user"""
    
    payload = {
        'user_id': user['id'],
        'email': user['email'],
        'exp': datetime.utcnow() + timedelta(days=30)  # Token expires in 30 days
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')

def create_response(status_code: int, body: Dict[str, Any]):
    """Create standard API response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(body)
    }