import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { DockerImageAsset, Platform } from 'aws-cdk-lib/aws-ecr-assets';
import { Construct } from 'constructs';
import * as path from 'path';

export interface DocTranslationStackProps extends cdk.StackProps {
  /** S3 bucket name for file storage */
  s3Bucket: string;
  /** JWT signing secret */
  jwtSecret: string;
  /** Resource name prefix (default: "doc-translation") */
  projectName?: string;
  /** Max parallel file processing (default: "5") */
  maxConcurrentFiles?: string;
  /** Cells/paragraphs per Bedrock API call (default: "10") */
  translationBatchSize?: string;
  /** Max upload size in bytes (default: "52428800") */
  maxFileSize?: string;
  /** Log level (default: "INFO") */
  logLevel?: string;
  /** Debug mode (default: "false") */
  debug?: string;
  /** Use ARM64 architecture for Fargate tasks and Docker builds (default: false / X86_64) */
  useArm64?: boolean;
  /** Enable an internal (non-internet-facing) ALB for private access (default: false) */
  enableInternalAlb?: boolean;
  /** VPC CIDR block (default: "10.0.0.0/16") */
  vpcCidr?: string;
  /** Comma-separated source CIDRs allowed to access the internal ALB on port 80 (default: "0.0.0.0/0").
   *  Use a single "0.0.0.0/0" for open access, or list specific CIDRs for stricter control.
   *  Example: "192.168.0.0/16,172.17.0.0/16,10.32.0.0/12" */
  internalAlbSourceCidr?: string;
}

export class DocTranslationStack extends cdk.Stack {
  /** VPC for all resources */
  public readonly vpc: ec2.Vpc;
  /** ALB security group - allows HTTP/HTTPS from anywhere */
  public readonly albSg: ec2.SecurityGroup;
  /** ECS tasks security group - allows traffic from ALB SG only */
  public readonly ecsSg: ec2.SecurityGroup;
  /** ECS execution role - pull images, write logs */
  public readonly executionRole: iam.Role;
  /** ECS task role - DynamoDB, Bedrock, S3 permissions */
  public readonly taskRole: iam.Role;
  /** ECS Fargate cluster */
  public readonly cluster: ecs.Cluster;
  /** Backend task definition */
  public readonly backendTaskDef: ecs.FargateTaskDefinition;
  /** Backend container definition (to add FRONTEND_URL env var in task 5) */
  public readonly backendContainer: ecs.ContainerDefinition;
  /** Backend Fargate service */
  public readonly backendService: ecs.FargateService;
  /** Frontend Fargate service */
  public readonly frontendService: ecs.FargateService;
  /** Application Load Balancer */
  public readonly alb: elbv2.ApplicationLoadBalancer;
  /** Internal ALB security group (created when enableInternalAlb is true) */
  public readonly internalAlbSg?: ec2.SecurityGroup;
  /** Internal Application Load Balancer (created when enableInternalAlb is true) */
  public readonly internalAlb?: elbv2.ApplicationLoadBalancer;

  constructor(scope: Construct, id: string, props: DocTranslationStackProps) {
    super(scope, id, props);

    const projectName = props.projectName ?? 'doc-translation';
    const useArm64 = props.useArm64 ?? false;
    const cpuArchitecture = useArm64 ? ecs.CpuArchitecture.ARM64 : ecs.CpuArchitecture.X86_64;
    const dockerPlatform = useArm64 ? Platform.LINUX_ARM64 : Platform.LINUX_AMD64;

    const vpcCidr = props.vpcCidr ?? '10.0.0.0/16';
    const internalAlbSourceCidr = props.internalAlbSourceCidr ?? '0.0.0.0/0';

    // --- VPC and Networking (Requirement 2) ---
    this.vpc = new ec2.Vpc(this, 'Vpc', {
      vpcName: `${projectName}-vpc`,
      ipAddresses: ec2.IpAddresses.cidr(vpcCidr),
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        { cidrMask: 24, name: 'Public', subnetType: ec2.SubnetType.PUBLIC },
        { cidrMask: 24, name: 'Private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      ],
      gatewayEndpoints: {
        S3: { service: ec2.GatewayVpcEndpointAwsService.S3 },
        DynamoDB: { service: ec2.GatewayVpcEndpointAwsService.DYNAMODB },
      },
    });

    // --- Security Groups (Requirement 6) ---

    // ALB Security Group: allows inbound HTTP (80) and HTTPS (443) from any source
    this.albSg = new ec2.SecurityGroup(this, 'AlbSg', {
      vpc: this.vpc,
      description: 'ALB Security Group',
    });
    this.albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'Allow HTTP from anywhere');
    this.albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'Allow HTTPS from anywhere');

    // ECS Security Group: allows inbound on ports 8000 and 8080 from ALB SG only
    this.ecsSg = new ec2.SecurityGroup(this, 'EcsSg', {
      vpc: this.vpc,
      description: 'ECS Tasks Security Group',
    });
    this.ecsSg.addIngressRule(this.albSg, ec2.Port.tcp(8000), 'Allow backend traffic from ALB');
    this.ecsSg.addIngressRule(this.albSg, ec2.Port.tcp(8080), 'Allow frontend traffic from ALB');

    // --- IAM Roles (Requirement 7) ---

    // Execution Role: used by ECS to pull images and write logs (Requirement 7.1)
    this.executionRole = new iam.Role(this, 'ExecutionRole', {
      roleName: `${projectName}-execution-role`,
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // Task Role: custom permissions for DynamoDB, Bedrock, and S3 (Requirements 7.2, 7.3, 7.4)
    this.taskRole = new iam.Role(this, 'TaskRole', {
      roleName: `${projectName}-task-role`,
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    // DynamoDB permissions scoped to doc_translation_* tables and their indexes (Requirement 7.2)
    this.taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
        'dynamodb:Query',
        'dynamodb:Scan',
        'dynamodb:BatchGetItem',
        'dynamodb:BatchWriteItem',
        'dynamodb:CreateTable',
        'dynamodb:DescribeTable',
      ],
      resources: [
        'arn:aws:dynamodb:*:*:table/doc_translation_*',
        'arn:aws:dynamodb:*:*:table/doc_translation_*/index/*',
      ],
    }));

    // Bedrock permissions on all resources (Requirement 7.3)
    this.taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
        'bedrock:Converse',
      ],
      resources: ['*'],
    }));

    // S3 permissions scoped to the configured bucket (Requirement 7.4)
    this.taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3:PutObject',
        's3:GetObject',
        's3:DeleteObject',
      ],
      resources: [`arn:aws:s3:::${props.s3Bucket}/*`],
    }));

    this.taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3:ListBucket',
      ],
      resources: [`arn:aws:s3:::${props.s3Bucket}`],
    }));

    // --- Docker Image Assets (Requirement 3) ---

    const backendImage = new DockerImageAsset(this, 'BackendImage', {
      directory: path.join(__dirname, '../../backend'),
      platform: dockerPlatform,
    });

    const frontendImage = new DockerImageAsset(this, 'FrontendImage', {
      directory: path.join(__dirname, '../../frontend'),
      buildArgs: { VITE_API_URL: '/api/graphql' },
      platform: dockerPlatform,
    });

    // --- ECS Cluster (Requirement 4.1) ---

    this.cluster = new ecs.Cluster(this, 'Cluster', {
      clusterName: `${projectName}-cluster`,
      vpc: this.vpc,
    });

    // --- Backend Task Definition and Service (Requirements 4.2, 4.4, 4.6, 4.8, 4.9, 7.5) ---

    const backendLogGroup = new logs.LogGroup(this, 'BackendLogGroup', {
      logGroupName: '/ecs/doc-translation-backend',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_MONTH,
    });

    this.backendTaskDef = new ecs.FargateTaskDefinition(this, 'BackendTaskDef', {
      cpu: 512,
      memoryLimitMiB: 1024,
      executionRole: this.executionRole,
      taskRole: this.taskRole,
      runtimePlatform: {
        cpuArchitecture,
        operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
      },
    });

    this.backendContainer = this.backendTaskDef.addContainer('backend', {
      image: ecs.ContainerImage.fromDockerImageAsset(backendImage),
      portMappings: [{ containerPort: 8000 }],
      environment: {
        AWS_REGION: this.region,
        JWT_SECRET: props.jwtSecret,
        S3_BUCKET: props.s3Bucket,
        MAX_CONCURRENT_FILES: props.maxConcurrentFiles ?? '5',
        TRANSLATION_BATCH_SIZE: props.translationBatchSize ?? '10',
        MAX_FILE_SIZE: props.maxFileSize ?? '52428800',
        LOG_LEVEL: props.logLevel ?? 'INFO',
        DEBUG: props.debug ?? 'false',
        // FRONTEND_URL will be added in task 5 when ALB is created
      },
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8000/api/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(60),
      },
      logging: ecs.LogDriver.awsLogs({
        logGroup: backendLogGroup,
        streamPrefix: 'backend',
      }),
    });

    this.backendService = new ecs.FargateService(this, 'BackendService', {
      cluster: this.cluster,
      taskDefinition: this.backendTaskDef,
      desiredCount: 1,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [this.ecsSg],
      assignPublicIp: false,
    });

    // --- Frontend Task Definition and Service (Requirements 4.3, 4.5, 4.7, 4.9, 7.6) ---

    const frontendLogGroup = new logs.LogGroup(this, 'FrontendLogGroup', {
      logGroupName: '/ecs/doc-translation-frontend',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_MONTH,
    });

    const frontendTaskDef = new ecs.FargateTaskDefinition(this, 'FrontendTaskDef', {
      cpu: 256,
      memoryLimitMiB: 512,
      executionRole: this.executionRole,
      // No task role for frontend (Requirement 7.6)
      runtimePlatform: {
        cpuArchitecture,
        operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
      },
    });

    frontendTaskDef.addContainer('frontend', {
      image: ecs.ContainerImage.fromDockerImageAsset(frontendImage),
      portMappings: [{ containerPort: 8080 }],
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8080/ || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(30),
      },
      logging: ecs.LogDriver.awsLogs({
        logGroup: frontendLogGroup,
        streamPrefix: 'frontend',
      }),
    });

    this.frontendService = new ecs.FargateService(this, 'FrontendService', {
      cluster: this.cluster,
      taskDefinition: frontendTaskDef,
      desiredCount: 1,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [this.ecsSg],
      assignPublicIp: false,
    });

    // --- Application Load Balancer (Requirement 5) ---

    // Task 5.1: Create internet-facing ALB in public subnets with ALB security group (Requirement 5.1)
    this.alb = new elbv2.ApplicationLoadBalancer(this, 'Alb', {
      vpc: this.vpc,
      internetFacing: true,
      securityGroup: this.albSg,
    });

    // Task 5.2: Create HTTP listener on port 80 with default action forwarding to frontend (Requirements 5.2, 5.4)
    const listener = this.alb.addListener('HttpListener', { port: 80 });

    // Default action: forward to frontend target group (port 8080, health check /)
    listener.addTargets('FrontendTarget', {
      port: 8080,
      targets: [this.frontendService],
      healthCheck: { path: '/' },
    });

    // Task 5.3: Path-based routing rule: /api/* forwards to backend target group (Requirement 5.3)
    listener.addTargets('BackendTarget', {
      port: 8000,
      targets: [this.backendService],
      priority: 10,
      conditions: [elbv2.ListenerCondition.pathPatterns(['/api/*'])],
      healthCheck: { path: '/api/health' },
    });

    // Add FRONTEND_URL environment variable to backend container now that ALB is created (Requirement 4.8)
    this.backendContainer.addEnvironment('FRONTEND_URL', `http://${this.alb.loadBalancerDnsName}`);

    // --- Auto Scaling (Requirement 8) ---

    // Backend auto-scaling: min 1, max 4, CPU target 70% (Requirements 8.1, 8.3, 8.4)
    const backendScaling = this.backendService.autoScaleTaskCount({
      minCapacity: 1,
      maxCapacity: 4,
    });
    backendScaling.scaleOnCpuUtilization('BackendCpuScaling', {
      targetUtilizationPercent: 70,
      scaleOutCooldown: cdk.Duration.seconds(60),
      scaleInCooldown: cdk.Duration.seconds(120),
    });

    // Frontend auto-scaling: min 1, max 4, CPU target 70% (Requirements 8.2, 8.3, 8.4)
    const frontendScaling = this.frontendService.autoScaleTaskCount({
      minCapacity: 1,
      maxCapacity: 4,
    });
    frontendScaling.scaleOnCpuUtilization('FrontendCpuScaling', {
      targetUtilizationPercent: 70,
      scaleOutCooldown: cdk.Duration.seconds(60),
      scaleInCooldown: cdk.Duration.seconds(120),
    });

    // --- CloudFormation Outputs (Requirement 5.5) ---

    new cdk.CfnOutput(this, 'AlbDnsName', {
      value: this.alb.loadBalancerDnsName,
      exportName: `${projectName}-alb-dns`,
    });

    new cdk.CfnOutput(this, 'ClusterName', {
      value: this.cluster.clusterName,
      exportName: `${projectName}-cluster-name`,
    });

    new cdk.CfnOutput(this, 'BackendTaskDefinition', {
      value: this.backendTaskDef.taskDefinitionArn,
      exportName: `${projectName}-backend-task-def`,
    });

    new cdk.CfnOutput(this, 'PrivateSubnets', {
      value: this.vpc.privateSubnets.map(s => s.subnetId).join(','),
      exportName: `${projectName}-private-subnets`,
    });

    new cdk.CfnOutput(this, 'EcsSecurityGroup', {
      value: this.ecsSg.securityGroupId,
      exportName: `${projectName}-ecs-sg`,
    });

    // --- Internal ALB for Private Access (optional) ---

    const enableInternalAlb = props.enableInternalAlb ?? false;
    if (enableInternalAlb) {
      this.internalAlbSg = new ec2.SecurityGroup(this, 'InternalAlbSg', {
        vpc: this.vpc,
        description: 'Internal ALB Security Group',
      });
      const sourceCidrs = internalAlbSourceCidr.split(',').map(c => c.trim()).filter(c => c.length > 0);
      for (const cidr of sourceCidrs) {
        const peer = cidr === '0.0.0.0/0' ? ec2.Peer.anyIpv4() : ec2.Peer.ipv4(cidr);
        this.internalAlbSg.addIngressRule(peer, ec2.Port.tcp(80), `Allow HTTP from ${cidr}`);
      }

      this.ecsSg.addIngressRule(this.internalAlbSg, ec2.Port.tcp(8000), 'Allow backend traffic from internal ALB');
      this.ecsSg.addIngressRule(this.internalAlbSg, ec2.Port.tcp(8080), 'Allow frontend traffic from internal ALB');

      this.internalAlb = new elbv2.ApplicationLoadBalancer(this, 'InternalAlb', {
        vpc: this.vpc,
        internetFacing: false,
        securityGroup: this.internalAlbSg,
        vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      });

      const internalListener = this.internalAlb.addListener('InternalHttpListener', { port: 80 });

      internalListener.addTargets('InternalFrontendTarget', {
        port: 8080,
        targets: [this.frontendService],
        healthCheck: { path: '/' },
      });

      internalListener.addTargets('InternalBackendTarget', {
        port: 8000,
        targets: [this.backendService],
        priority: 10,
        conditions: [elbv2.ListenerCondition.pathPatterns(['/api/*'])],
        healthCheck: { path: '/api/health' },
      });

      new cdk.CfnOutput(this, 'InternalAlbDnsName', {
        value: this.internalAlb.loadBalancerDnsName,
        exportName: `${projectName}-internal-alb-dns`,
      });
    }
  }
}
