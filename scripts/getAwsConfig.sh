#!/bin/bash

echo "Ì¥ç GETTING YOUR AWS CONFIGURATION VALUES"
echo "========================================"

echo ""
echo "1Ô∏è‚É£  COGNITO USER POOLS:"
echo "------------------------"
aws cognito-idp list-user-pools --max-items 20 --query 'UserPools[].{Name:Name,Id:Id}' --output table

echo ""
echo "2Ô∏è‚É£  DYNAMODB TABLES:"
echo "-------------------"
aws dynamodb list-tables --query 'TableNames[?contains(@, `certtracker`) || contains(@, `user`) || contains(@, `cert`)]' --output table

echo ""
echo "3Ô∏è‚É£  S3 BUCKETS:"
echo "-------------"
aws s3 ls | grep -E "(certtracker|cert|document)"

echo ""
echo "4Ô∏è‚É£  API GATEWAY:"
echo "--------------"
aws apigateway get-rest-apis --query 'items[?contains(name, `certtracker`) || contains(name, `cert`)].{Name:name,Id:id}' --output table

echo ""
echo "Ì≥ã NEXT STEPS:"
echo "============="
echo "1. Copy your User Pool ID from section 1"
echo "2. Get Client ID with: aws cognito-idp list-user-pool-clients --user-pool-id YOUR_USER_POOL_ID"
echo "3. Update .env file with your actual values"
echo "4. Update src/services/awsConfig.ts with your configuration"

echo ""
echo "Ì≤° Quick command to get client ID (replace USER_POOL_ID):"
echo "aws cognito-idp list-user-pool-clients --user-pool-id us-east-1_XXXXXXXXX --query 'UserPoolClients[].{Name:ClientName,Id:ClientId}' --output table"
