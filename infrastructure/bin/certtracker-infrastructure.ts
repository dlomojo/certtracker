#!/usr/bin/env node
// infrastructure/bin/certtracker-infrastructure.ts
import * as cdk from 'aws-cdk-lib';
import 'source-map-support/register';
import { CertTrackerStack } from '../lib/certtracker-stack';

const app = new cdk.App();
new CertTrackerStack(app, 'CertTrackerStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  tags: {
    project: 'CertTracker',
    environment: process.env.ENVIRONMENT || 'dev',
  },
});