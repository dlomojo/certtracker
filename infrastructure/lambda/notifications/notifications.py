import json
import boto3
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

# Environment variables
CERTIFICATIONS_TABLE = os.environ.get('CERTIFICATIONS_TABLE')
USERS_TABLE = os.environ.get('USERS_TABLE')

def handler(event, context):
    """Check for expiring certifications and send email reminders"""
    
    logger.info("Starting certification expiration check...")
    
    try:
        certs_table = dynamodb.Table(CERTIFICATIONS_TABLE)
        users_table = dynamodb.Table(USERS_TABLE)
        
        notifications_sent = 0
        today = datetime.now().date()
        
        # Check for certifications expiring in 30, 60, 90 days
        for days_ahead in [30, 60, 90]:
            target_date = today + timedelta(days=days_ahead)
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            logger.info(f"Checking for certifications expiring on {target_date_str}")
            
            # Scan for expiring certifications
            response = certs_table.scan(
                FilterExpression='expiryDate = :date AND #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':date': target_date_str,
                    ':status': 'active'
                }
            )
            
            for cert in response.get('Items', []):
                # Get user details
                user_response = users_table.get_item(
                    Key={'userId': cert['userId']}
                )
                
                if 'Item' in user_response:
                    user = user_response['Item']
                    success = send_expiration_email(
                        user['email'], 
                        user['name'],
                        cert['name'], 
                        cert['provider'],
                        days_ahead
                    )
                    if success:
                        notifications_sent += 1
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Notification check completed. Sent {notifications_sent} notifications.'
            })
        }
        
    except Exception as e:
        logger.error(f"Error in notification handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def send_expiration_email(user_email, user_name, cert_name, provider, days_until_expiry):
    """Send expiration reminder email via SES"""
    
    try:
        subject = f"🚨 {cert_name} expires in {days_until_expiry} days"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">🛡️ CertTracker Alert</h1>
            </div>
            
            <div style="padding: 30px; background: #f9fafb;">
                <h2 style="color: #111827;">Hi {user_name},</h2>
                
                <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <h3 style="color: #d97706; margin-top: 0;">⚠️ Certification Expiring Soon</h3>
                    <p><strong>{cert_name}</strong> from <strong>{provider}</strong> will expire in <strong>{days_until_expiry} days</strong>.</p>
                </div>
                
                <div style="margin: 20px 0;">
                    <h4>Next Steps:</h4>
                    <ul>
                        <li>Check renewal requirements</li>
                        <li>Schedule your renewal exam</li>
                        <li>Complete any required CPE credits</li>
                        <li>Update your certification in CertTracker</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://d30p8wd4n2r02p.cloudfront.net" 
                       style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                        View in CertTracker
                    </a>
                </div>
                
                <p style="color: #6b7280; font-size: 14px; text-align: center;">
                    Stay ahead of your certification renewals with CertTracker.<br>
                    This is an automated reminder from your CertTracker account.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        CertTracker Certification Alert
        
        Hi {user_name},
        
        Your {cert_name} certification from {provider} will expire in {days_until_expiry} days.
        
        Next Steps:
        - Check renewal requirements
        - Schedule your renewal exam  
        - Complete any required CPE credits
        - Update your certification in CertTracker
        
        View your certifications: https://d30p8wd4n2r02p.cloudfront.net
        
        This is an automated reminder from CertTracker.
        """
        
        response = ses.send_email(
            Source='noreply@yourdomain.com',  # Update this to your verified SES email
            Destination={'ToAddresses': [user_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                }
            }
        )
        
        logger.info(f"Email sent to {user_email} for {cert_name}. MessageId: {response['MessageId']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {user_email}: {str(e)}")
        return False