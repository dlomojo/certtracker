#!/bin/bash
set -e

echo "🚀 Setting up CertTracker development environment..."

# Check prerequisites
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI is required"; exit 1; }

# Install CDK globally if not present
if ! command -v cdk &> /dev/null; then
    echo "📦 Installing AWS CDK..."
    npm install -g aws-cdk
fi

# Setup infrastructure
echo "🏗️ Setting up infrastructure..."
cd infrastructure
npm install
cd ..

# Setup Python environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install boto3 pytest moto

echo "✅ Setup complete!"
echo "💡 Next steps:"
echo "   1. Configure AWS CLI: aws configure"
echo "   2. Bootstrap CDK: cd infrastructure && cdk bootstrap"
echo "   3. Deploy: cd infrastructure && npm run deploy"
