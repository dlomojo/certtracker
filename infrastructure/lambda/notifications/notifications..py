# infrastructure/lambda/notifications/notifications.py
import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

def handler(event, context):
    """
    Check for expiring certifications and send notifications
    Triggered daily by CloudWatch Events
    """
    
    print("Starting certification expiration check...")
    
    try:
        # Initialize AWS clients
        dynamodb = boto3.resource('dynamodb')
        ses = boto3.client('ses')
        
        # Get table names from environment
        certs_table_name = os.environ['CERTIFICATIONS_TABLE']
        users_table_name = os.environ['USERS_TABLE']
        
        certs_table = dynamodb.Table(certs_table_name)
        users_table = dynamodb.Table(users_table_name)
        
        # Check for certifications expiring in 30, 60, and 90 days
        notifications_sent = 0
        
        for days_ahead in [30, 60, 90]:
            target_date = datetime.now() + timedelta(days=days_ahead)
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            print(f"Checking for certifications expiring on {target_date_str}")
            
            # TODO: Query DynamoDB for expiring certifications
            # For now, just log the check
            print(f"Would check for certifications expiring in {days_ahead} days")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Notification check completed. Sent {notifications_sent} notifications.'
            })
        }
        
    except Exception as e:
        print(f"Error in notification handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process notifications',
                'details': str(e)
            })
        }

def send_expiration_email(user_email, certification_name, days_until_expiry):
    """Send expiration reminder email"""
    
    ses = boto3.client('ses')
    
    subject = f"Certification Expiring Soon: {certification_name}"
    
    body_text = f"""
    Hello,
    
    Your {certification_name} certification will expire in {days_until_expiry} days.
    
    Please make sure to renew it before it expires.
    
    Best regards,
    CertTracker Team
    """
    
    body_html = f"""
    <html>
    <head></head>
    <body>
        <h2>Certification Expiring Soon</h2>
        <p>Hello,</p>
        <p>Your <strong>{certification_name}</strong> certification will expire in <strong>{days_until_expiry} days</strong>.</p>
        <p>Please make sure to renew it before it expires.</p>
        <p>Best regards,<br>CertTracker Team</p>
    </body>
    </html>
    """
    
    try:
        response = ses.send_email(
            Source='noreply@yourdomain.com',  # Change this to your verified email
            Destination={'ToAddresses': [user_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': body_text, 'Charset': 'UTF-8'},
                    'Html': {'Data': body_html, 'Charset': 'UTF-8'}
                }
            }
        )
        
        print(f"Email sent successfully to {user_email}. MessageId: {response['MessageId']}")
        return True
        
    except Exception as e:
        print(f"Failed to send email to {user_email}: {str(e)}")
        return False