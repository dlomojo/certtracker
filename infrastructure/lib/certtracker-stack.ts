// infrastructure/lib/certtracker-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ses from 'aws-cdk-lib/aws-ses';
import { Construct } from 'constructs';

export class CertTrackerStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // DynamoDB Tables (Free Tier: 25GB storage)
    const usersTable = new dynamodb.Table(this, 'UsersTable', {
      tableName: 'CertTracker-Users',
      partitionKey: { name: 'userId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const certificationsTable = new dynamodb.Table(this, 'CertificationsTable', {
      tableName: 'CertTracker-Certifications',
      partitionKey: { name: 'userId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'certId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Add GSI for querying by expiration date
    certificationsTable.addGlobalSecondaryIndex({
      indexName: 'ExpirationDateIndex',
      partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'expirationDate', type: dynamodb.AttributeType.STRING },
    });

    // Cognito User Pool (Free Tier: 50K MAU)
    const userPool = new cognito.UserPool(this, 'CertTrackerUserPool', {
      userPoolName: 'CertTracker-Users',
      selfSignUpEnabled: true,
      signInAliases: { email: true },
      autoVerify: { email: true },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
      },
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const userPoolClient = new cognito.UserPoolClient(this, 'CertTrackerUserPoolClient', {
      userPool,
      generateSecret: false,
      authFlows: {
        userPassword: true,
        userSrp: true,
        adminUserPassword: true,
      },
    });

    // Lambda Functions
    const apiLambda = new lambda.Function(this, 'ApiLambda', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'api.handler',
      code: lambda.Code.fromAsset('lambda/api'),
      environment: {
        USERS_TABLE: usersTable.tableName,
        CERTIFICATIONS_TABLE: certificationsTable.tableName,
        USER_POOL_ID: userPool.userPoolId,
        USER_POOL_CLIENT_ID: userPoolClient.userPoolClientId,
      },
      timeout: cdk.Duration.seconds(30),
    });

    const notificationLambda = new lambda.Function(this, 'NotificationLambda', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'notifications.handler',
      code: lambda.Code.fromAsset('lambda/notifications'),
      environment: {
        CERTIFICATIONS_TABLE: certificationsTable.tableName,
        USERS_TABLE: usersTable.tableName,
      },
      timeout: cdk.Duration.minutes(5),
    });

    // Grant permissions
    usersTable.grantReadWriteData(apiLambda);
    certificationsTable.grantReadWriteData(apiLambda);
    certificationsTable.grantReadData(notificationLambda);
    usersTable.grantReadData(notificationLambda);

    // Grant Cognito permissions to API Lambda
    apiLambda.addToRolePolicy(new iam.PolicyStatement({
    actions: [
    'cognito-idp:AdminCreateUser',
    'cognito-idp:AdminSetUserPassword', 
    'cognito-idp:AdminInitiateAuth',
    'cognito-idp:AdminGetUser'
      ],
      resources: [userPool.userPoolArn],
    }));

    // Grant SES permissions
    notificationLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendEmail', 'ses:SendRawEmail'],
      resources: ['*'],
    }));

    // API Gateway (Free Tier: 1M requests/month)
    const api = new apigateway.RestApi(this, 'CertTrackerApi', {
      restApiName: 'CertTracker API',
      description: 'API for CertTracker application',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key'],
      },
    });

    // Cognito Authorizer
    const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
      cognitoUserPools: [userPool],
    });

    // API Routes
    const apiIntegration = new apigateway.LambdaIntegration(apiLambda);
    
    // Public auth routes
    const authResource = api.root.addResource('auth');
    authResource.addMethod('POST', apiIntegration);
    
    // Protected certification routes
    const certResource = api.root.addResource('certifications');
    certResource.addMethod('GET', apiIntegration, { authorizer: cognitoAuthorizer });
    certResource.addMethod('POST', apiIntegration, { authorizer: cognitoAuthorizer });
    
    const certItemResource = certResource.addResource('{id}');
    certItemResource.addMethod('GET', apiIntegration, { authorizer: cognitoAuthorizer });
    certItemResource.addMethod('PUT', apiIntegration, { authorizer: cognitoAuthorizer });
    certItemResource.addMethod('DELETE', apiIntegration, { authorizer: cognitoAuthorizer });

    // S3 Bucket for Frontend (Free Tier: 5GB storage)
    const websiteBucket = new s3.Bucket(this, 'WebsiteBucket', {
      bucketName: `certtracker-frontend-${this.account}`,
      websiteIndexDocument: 'index.html',
      websiteErrorDocument: 'error.html',
      publicReadAccess: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ACLS,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // CloudFront Distribution
    const distribution = new cloudfront.Distribution(this, 'WebsiteDistribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(websiteBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
      defaultRootObject: 'index.html',
      errorResponses: [{
        httpStatus: 404,
        responseHttpStatus: 200,
        responsePagePath: '/index.html',
      }],
    });

    // CloudWatch Event Rule for notifications
    const notificationRule = new events.Rule(this, 'NotificationRule', {
      schedule: events.Schedule.rate(cdk.Duration.days(1)),
      description: 'Daily certification expiration check',
    });

    notificationRule.addTarget(new targets.LambdaFunction(notificationLambda));

    // SES Email Identity
    const emailIdentity = new ses.EmailIdentity(this, 'SenderEmailIdentity', {
      identity: ses.Identity.email('noreply@yourdomain.com'), // Change this!
    });

    // Outputs
    new cdk.CfnOutput(this, 'WebsiteURL', {
      value: `https://${distribution.distributionDomainName}`,
      description: 'CloudFront Distribution URL',
    });

    new cdk.CfnOutput(this, 'ApiURL', {
      value: api.url,
      description: 'API Gateway URL',
    });

    new cdk.CfnOutput(this, 'UserPoolId', {
      value: userPool.userPoolId,
      description: 'Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
    });

    new cdk.CfnOutput(this, 'S3BucketName', {
      value: websiteBucket.bucketName,
      description: 'S3 Bucket for frontend',
    });

    new cdk.CfnOutput(this, 'CloudFrontDistributionId', {
      value: distribution.distributionId,
      description: 'CloudFront Distribution ID',
    });
  }
}