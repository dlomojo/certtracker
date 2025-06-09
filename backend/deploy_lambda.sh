echo "🚀 DEPLOYING LAMBDA FUNCTIONS"
echo "============================="

# Package Lambda functions
echo "📦 Packaging Lambda functions..."

# Create deployment packages
rm -rf dist/
mkdir -p dist/

# Auth handler
echo "📦 Packaging auth handler..."
cp auth_handler.py dist/
pip install -r requirements.txt -t dist/
cd dist && zip -r ../auth_handler.zip . && cd ..
rm -rf dist/*

# Certifications handler
echo "📦 Packaging certifications handler..."
cp certifications_handler.py dist/
cp auth_handler.py dist/  # For shared functions
pip install -r requirements.txt -t dist/
cd dist && zip -r ../certifications_handler.zip . && cd ..
rm -rf dist/*

# Upload handler
echo "📦 Packaging upload handler..."
cp upload_handler.py dist/
cp auth_handler.py dist/  # For shared functions
pip install -r requirements.txt -t dist/
cd dist && zip -r ../upload_handler.zip . && cd ..

# Deploy Lambda functions
echo "🚀 Deploying Lambda functions..."

# Get function names from AWS
AUTH_FUNCTION=$(aws lambda list-functions --query 'Functions[?contains(FunctionName, `auth`) || contains(FunctionName, `Auth`)].FunctionName' --output text | head -1)
CERT_FUNCTION=$(aws lambda list-functions --query 'Functions[?contains(FunctionName, `cert`) || contains(FunctionName, `Cert`)].FunctionName' --output text | head -1)
UPLOAD_FUNCTION=$(aws lambda list-functions --query 'Functions[?contains(FunctionName, `upload`) || contains(FunctionName, `Upload`)].FunctionName' --output text | head -1)

if [ -n "$AUTH_FUNCTION" ]; then
    echo "📤 Updating auth function: $AUTH_FUNCTION"
    aws lambda update-function-code \
        --function-name $AUTH_FUNCTION \
        --zip-file fileb://auth_handler.zip
fi

if [ -n "$CERT_FUNCTION" ]; then
    echo "📤 Updating certifications function: $CERT_FUNCTION"
    aws lambda update-function-code \
        --function-name $CERT_FUNCTION \
        --zip-file fileb://certifications_handler.zip
fi

if [ -n "$UPLOAD_FUNCTION" ]; then
    echo "📤 Updating upload function: $UPLOAD_FUNCTION"
    aws lambda update-function-code \
        --function-name $UPLOAD_FUNCTION \
        --zip-file fileb://upload_handler.zip
fi

# Clean up
rm -rf dist/
rm -f *.zip

echo ""
echo "✅ LAMBDA DEPLOYMENT COMPLETE!"
echo ""
echo "🔧 Next steps:"
echo "1. Update environment variables in Lambda console"
echo "2. Test API endpoints"
echo "3. Update CORS settings if needed"