# ECS Fargate CDK Deployment Guide

Deploy the Doc Translation System to Amazon ECS Fargate using AWS CDK.

## Prerequisites

1. Node.js 18+ and npm
2. AWS CLI installed and configured
3. Docker installed and running
4. AWS CDK CLI (`npm install -g aws-cdk`)
5. AWS IAM user/role with the following permissions:
   - Full access to ECS, ECR, VPC, ELB, IAM, CloudFormation
   - Access to DynamoDB, S3, Bedrock
6. S3 bucket created for file storage
7. Bedrock model access enabled in your AWS account (Nova 2 Lite, Claude Sonnet/Haiku)

## Deployment Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                         VPC                              │
                    │  ┌─────────────────────────────────────────────────────┐ │
                    │  │                   Public Subnets                     │ │
Internet ──────────►│  │  ┌─────────────────────────────────────────────┐    │ │
                    │  │  │     Public Application Load Balancer        │    │ │
                    │  │  │   /:80 → Frontend    /api/*:80 → Backend    │    │ │
                    │  │  └─────────────────────────────────────────────┘    │ │
                    │  └─────────────────────────────────────────────────────┘ │
                    │  ┌─────────────────────────────────────────────────────┐ │
                    │  │                  Private Subnets                     │ │
                    │  │  ┌──────────────────┐    ┌──────────────────┐       │ │
                    │  │  │  ECS Service     │    │  ECS Service     │       │ │
                    │  │  │  (Frontend)      │    │  (Backend)       │       │ │
                    │  │  │  Nginx :8080     │    │  Uvicorn :8000   │       │ │
                    │  │  └──────────────────┘    └──────────────────┘       │ │
VPN / Direct ──────►│  │  ┌─────────────────────────────────────────────┐    │ │
Connect / Peering   │  │  │    Internal Application Load Balancer *     │    │ │
                    │  │  │   /:80 → Frontend    /api/*:80 → Backend    │    │ │
                    │  │  └─────────────────────────────────────────────┘    │ │
                    │  └─────────────────────────────────────────────────────┘ │
                    └─────────────────────────────────────────────────────────┘
                              * Optional: enabled with enableInternalAlb
                                                        │
                                              ┌─────────┼─────────┐
                                              ▼         ▼         ▼
                                          DynamoDB   Bedrock      S3
```

## Quick Start

```bash
cd ecs
npm install

# Set required environment variables
export AWS_REGION=your-region-code
export S3_BUCKET=your-s3-bucket-name
# Use: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
export JWT_SECRET=your-jwt-secret-key

# Create S3 bucket (if not already created)
aws s3 mb s3://$S3_BUCKET --region $AWS_REGION

# Bootstrap CDK (only required once per AWS account/region)
npx cdk bootstrap

# Deploy
npx cdk deploy
```

## Configuration Parameters

Parameters are provided via CDK context (`-c`) or environment variables. Context takes precedence:

| Parameter | Environment Variable | Required | Description |
|-----------|---------------------|----------|-------------|
| `s3Bucket` | `S3_BUCKET` | Yes | S3 bucket name for file storage |
| `jwtSecret` | `JWT_SECRET` | Yes | JWT signing secret |
| `region` | `CDK_DEFAULT_REGION` | No | AWS region (default: us-west-2) |
| `cpuArch` | `CPU_ARCH` | No | CPU architecture: `arm64` or `x64` (auto-detected from host) |
| `enableInternalAlb` | `ENABLE_INTERNAL_ALB` | No | Enable internal ALB for private access (default: `false`) |
| - | `CDK_DEFAULT_ACCOUNT` | No | AWS account ID (auto-detected) |

## CDK Commands

```bash
npx cdk synth          # Generate CloudFormation template
npx cdk diff           # View change diff
npx cdk deploy         # Deploy stack
npx cdk destroy        # Delete all resources
```

## Internal ALB (Optional)

Enable the internal ALB to allow private access from within the VPC or connected networks (VPN, Direct Connect, VPC Peering, Transit Gateway) without traversing the public internet. This also serves as the foundation for AWS PrivateLink if cross-account access is needed later.

```bash
# Deploy with internal ALB enabled
npx cdk deploy -c enableInternalAlb=true

# Or via environment variable
export ENABLE_INTERNAL_ALB=true
npx cdk deploy
```

When enabled, this creates:
- An internal (non-internet-facing) ALB in private subnets
- A security group allowing HTTP (port 80) from the VPC CIDR
- The same routing rules as the public ALB (`/` to frontend, `/api/*` to backend)
- A CloudFormation output `InternalAlbDnsName` with the internal DNS name

The internal ALB DNS name is only resolvable from within the VPC or connected networks.

## Post-Deployment

### Get Access URL

After deployment, CDK outputs the ALB DNS address:

```
Outputs:
DocTranslationStack.AlbDnsName = DocTr-Alb-xxxxx.us-west-2.elb.amazonaws.com
```

You can also query via CloudFormation:

```bash
aws cloudformation describe-stacks \
  --stack-name DocTranslationStack \
  --query 'Stacks[0].Outputs[?OutputKey==`AlbDnsName`].OutputValue' \
  --output text
```

## Resource Details

### ECS Services

| Service | CPU | Memory | Port | Auto-scaling |
|---------|-----|--------|------|--------------|
| Backend | 0.5 vCPU | 1 GB | 8000 | 1-4 instances, CPU 70% |
| Frontend | 0.25 vCPU | 0.5 GB | 8080 | 1-4 instances, CPU 70% |

### Network

- VPC CIDR: 10.0.0.0/16, 2 availability zones
- Public subnets: Public ALB
- Private subnets: ECS tasks (internet access via NAT Gateway), Internal ALB (if enabled)
- VPC Gateway Endpoints: S3, DynamoDB (no NAT charges)

### IAM Permissions

- Execution role: ECR image pull, CloudWatch log writes
- Task role (Backend only): DynamoDB (`doc_translation_*` tables), Bedrock (InvokeModel/Converse), S3 (configured bucket)

### CloudFormation Outputs

| Output | Description |
|--------|-------------|
| `AlbDnsName` | Public ALB DNS address |
| `InternalAlbDnsName` | Internal ALB DNS address (only when `enableInternalAlb` is true) |
| `ClusterName` | ECS cluster name |
| `BackendTaskDefinition` | Backend task definition ARN |
| `PrivateSubnets` | Private subnet ID list |
| `EcsSecurityGroup` | ECS security group ID |

## Troubleshooting

### View Service Logs

```bash
aws logs tail /ecs/doc-translation-backend --follow
aws logs tail /ecs/doc-translation-frontend --follow
```

### Check Task Status

```bash
aws ecs describe-services \
  --cluster doc-translation-cluster \
  --services DocTranslationStack-BackendService* \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount}'
```

### Common Issues

- Task fails to start: Check if Docker image built successfully, view CloudWatch logs
- Health check fails: Verify container port and health check path are correct (Backend: `/api/health`, Frontend: `/`)
- Bedrock calls fail: Confirm model access is enabled in the target region

## Cost Estimation

| Resource | Configuration | Estimated Monthly Cost |
|----------|--------------|------------------------|
| ECS Fargate (Backend) | 0.5 vCPU, 1GB | ~$15 |
| ECS Fargate (Frontend) | 0.25 vCPU, 0.5GB | ~$8 |
| ALB (public) | Base fee + LCU | ~$20 |
| ALB (internal, optional) | Base fee + LCU | ~$20 |
| NAT Gateway | 1 instance | ~$35 |
| DynamoDB | On-demand capacity | ~$5 |
| S3 | File storage | ~$1 |
| **Total** | | **~$84/month** |

*Actual costs depend on usage. Bedrock API call costs are additional. Internal ALB adds ~$20/month when enabled.*

---

[Back to main README](../README.md)
