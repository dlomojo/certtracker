#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: deploy_frontend.sh <s3-bucket-name>"
  exit 1
fi

BUCKET=$1

cd "$(dirname "$0")/../frontend"

if [ ! -d node_modules ]; then
  npm install
fi

npm run build
aws s3 sync dist "s3://$BUCKET" --delete

