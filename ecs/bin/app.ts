#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { DocTranslationStack } from '../lib/doc-translation-stack';
import * as os from 'os';

const app = new cdk.App();

// Configuration resolution: CDK context first, then environment variables
const s3Bucket = app.node.tryGetContext('s3Bucket') || process.env.S3_BUCKET;
if (!s3Bucket) {
  throw new Error(
    'Missing required configuration: s3Bucket. Provide via -c s3Bucket=<name> or S3_BUCKET env var.'
  );
}

const jwtSecret = app.node.tryGetContext('jwtSecret') || process.env.JWT_SECRET;
if (!jwtSecret) {
  throw new Error(
    'Missing required configuration: jwtSecret. Provide via -c jwtSecret=<secret> or JWT_SECRET env var.'
  );
}

// Default region to us-west-2
const region = app.node.tryGetContext('region') || process.env.CDK_DEFAULT_REGION || 'us-west-2';
const account = process.env.CDK_DEFAULT_ACCOUNT;

// Optional tunable configs: CDK context > env var > hardcoded default
const maxConcurrentFiles = app.node.tryGetContext('maxConcurrentFiles') || process.env.MAX_CONCURRENT_FILES || '5';
const translationBatchSize = app.node.tryGetContext('translationBatchSize') || process.env.TRANSLATION_BATCH_SIZE || '10';
const maxFileSize = app.node.tryGetContext('maxFileSize') || process.env.MAX_FILE_SIZE || '52428800';
const logLevel = app.node.tryGetContext('logLevel') || process.env.LOG_LEVEL || 'INFO';
const debug = app.node.tryGetContext('debug') || process.env.DEBUG || 'false';

// CPU architecture: detect from host, allow override via context or env var
// os.arch() returns 'arm64' on ARM64, 'x64' on x86_64
const cpuArch = app.node.tryGetContext('cpuArch') || process.env.CPU_ARCH || os.arch();
const useArm64 = cpuArch === 'arm64';

const enableInternalAlb = (app.node.tryGetContext('enableInternalAlb') ?? process.env.ENABLE_INTERNAL_ALB ?? 'false') === 'true';

const vpcCidr = app.node.tryGetContext('vpcCidr') || process.env.VPC_CIDR || '10.0.0.0/16';
const internalAlbSourceCidr = app.node.tryGetContext('internalAlbSourceCidr') || process.env.INTERNAL_ALB_SOURCE_CIDR || '0.0.0.0/0';

new DocTranslationStack(app, 'DocTranslationStack', {
  s3Bucket,
  jwtSecret,
  maxConcurrentFiles,
  translationBatchSize,
  maxFileSize,
  logLevel,
  debug,
  useArm64,
  enableInternalAlb,
  vpcCidr,
  internalAlbSourceCidr,
  env: {
    region,
    account,
  },
});
