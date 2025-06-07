# CertTracker

A serverless web application for tracking IT certifications and sending expiration reminders.

## Features

- 🔐 User authentication with AWS Cognito
- 📋 Track multiple IT certifications (CompTIA, Cisco, AWS, Azure, etc.)
- 📧 Automatic email reminders before expiration
- 💰 Ultra-low cost AWS serverless architecture
- 🚀 One-click deployment with CDK

## Quick Start

1. **Setup project:**
   ```bash
   ./scripts/setup.sh
   ```

2. **Configure AWS CLI:**
   ```bash
   aws configure
   ```

3. **Deploy infrastructure:**
   ```bash
   cd infrastructure
   npm run bootstrap  # One-time CDK setup
   npm run deploy
   ```

## Architecture

- **Frontend**: React SPA hosted on S3 + CloudFront
- **Backend**: AWS Lambda + API Gateway  
- **Database**: DynamoDB
- **Authentication**: AWS Cognito
- **Notifications**: SES + CloudWatch Events

## Development

- **VS Code**: Optimized for VS Code with debugging support
- **Local Development**: Python virtual environment for Lambda testing
- **Hot Reload**: Frontend development server
- **Infrastructure**: CDK for infrastructure as code

## Cost

Designed to stay within AWS free tier:
- Estimated cost: $0-5/month
- Serverless architecture scales to zero
- No idle server costs

## Tech Stack

- **Infrastructure**: AWS CDK (TypeScript)
- **Backend**: Python + AWS Lambda
- **Frontend**: React + TypeScript
- **Database**: DynamoDB
- **CI/CD**: GitHub Actions
