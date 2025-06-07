# infrastructure/lambda/api/api.py
import json
import boto3
import os
from datetime import datetime
import uuid

def handler(event, context):
    """
    Main API handler for CertTracker
    Routes requests to appropriate functions
    """
    
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Get HTTP method and path
        http_method = event.get('httpMethod')
        path = event.get('path', '/')
        
        # Handle different routes
        if path.startswith('/auth'):
            return handle_auth(event, context)
        elif path.startswith('/certifications'):
            return handle_certifications(event, context)
        else:
            return {
                'statusCode': 404,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Route not found'})
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }

def handle_auth(event, context):
    """Handle authentication related requests"""
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': json.dumps({'message': 'Auth endpoint - to be implemented'})
    }

def handle_certifications(event, context):
    """Handle certification CRUD operations"""
    
    http_method = event.get('httpMethod')
    path_parameters = event.get('pathParameters') or {}
    
    if http_method == 'GET':
        if 'id' in path_parameters:
            return get_certification(event, context)
        else:
            return list_certifications(event, context)
    elif http_method == 'POST':
        return create_certification(event, context)
    elif http_method == 'PUT':
        return update_certification(event, context)
    elif http_method == 'DELETE':
        return delete_certification(event, context)
    else:
        return {
            'statusCode': 405,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': 'Method not allowed'})
        }

def list_certifications(event, context):
    """List all certifications for a user"""
    # TODO: Get user ID from Cognito JWT token
    # For now, return mock data
    
    mock_certifications = [
        {
            'certId': '1',
            'name': 'CompTIA Security+',
            'provider': 'CompTIA',
            'issueDate': '2022-01-15',
            'expirationDate': '2025-01-15',
            'status': 'active'
        },
        {
            'certId': '2', 
            'name': 'AWS Solutions Architect',
            'provider': 'AWS',
            'issueDate': '2023-06-01',
            'expirationDate': '2026-06-01',
            'status': 'active'
        }
    ]
    
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': json.dumps(mock_certifications)
    }

def get_certification(event, context):
    """Get a specific certification"""
    cert_id = event['pathParameters']['id']
    
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'certId': cert_id,
            'message': f'Get certification {cert_id} - to be implemented'
        })
    }

def create_certification(event, context):
    """Create a new certification"""
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Basic validation
        required_fields = ['name', 'provider', 'issueDate', 'expirationDate']
        for field in required_fields:
            if field not in body:
                return {
                    'statusCode': 400,
                    'headers': get_cors_headers(),
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # TODO: Save to DynamoDB
        cert_id = str(uuid.uuid4())
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'certId': cert_id,
                'message': 'Certification created successfully'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }

def update_certification(event, context):
    """Update an existing certification"""
    cert_id = event['pathParameters']['id']
    
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'certId': cert_id,
            'message': f'Update certification {cert_id} - to be implemented'
        })
    }

def delete_certification(event, context):
    """Delete a certification"""
    cert_id = event['pathParameters']['id']
    
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'certId': cert_id,
            'message': f'Delete certification {cert_id} - to be implemented'
        })
    }

def get_cors_headers():
    """Return CORS headers for API responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Content-Type': 'application/json'
    }