# Backend Unit — Deployment Architecture

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-25  

---

## Deployment Architecture Specifications

Detailed configurations for deploying the Backend unit across development, staging, and production environments.

---

## Development Environment - Docker Compose

### Directory Structure

```
archery-backend/
├── Dockerfile
├── docker-compose.yml
├── docker-compose.override.yml
├── pyproject.toml
├── poetry.lock
├── src/
│   ├── main.py
│   ├── api/
│   ├── services/
│   ├── database/
│   ├── models/
│   └── ...
├── tests/
│   ├── unit/
│   └── integration/
├── scripts/
│   ├── init.sql
│   ├── seed.py
│   └── migrate.py
├── storage/
│   ├── raw/
│   ├── annotated/
│   └── archives/
├── logs/
├── .env.example
└── README.md
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    opencv-python-headless \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Copy application code
COPY src/ ./src
COPY scripts/ ./scripts

# Create storage directories
RUN mkdir -p /storage/{raw,annotated,archives} && \
    chmod 755 /storage

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Configuration

**docker-compose.yml** (shared):

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: archery_api_dev
    environment:
      DATABASE_URL: postgresql://archery_user:archery_password@postgres:5432/archery_dev
      REDIS_URL: redis://redis:6379/0
      ENVIRONMENT: development
      LOG_LEVEL: INFO
      CORS_ORIGINS: "http://localhost:3000,http://localhost:8080"
      JWT_SECRET: ${JWT_SECRET_DEV:-dev-secret-change-in-prod}
      JWT_ALGORITHM: HS256
      JWT_EXPIRATION_HOURS: 8
      STORAGE_PATH: /storage
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./src:/app/src
      - ./storage:/storage
      - ./logs:/app/logs
    networks:
      - archery-network
    command: |
      sh -c "poetry run alembic upgrade head && \
             python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"

  postgres:
    image: postgres:15-alpine
    container_name: archery_db_dev
    environment:
      POSTGRES_USER: archery_user
      POSTGRES_PASSWORD: archery_password
      POSTGRES_DB: archery_dev
      POSTGRES_INITDB_ARGS: "-c shared_buffers=256MB -c max_connections=20"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - archery-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U archery_user -d archery_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: archery_cache_dev
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - archery-network
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  archery-network:
    driver: bridge
```

**docker-compose.override.yml** (dev overrides):

```yaml
# This file is loaded automatically by docker-compose for local development
# Use it to override settings for development-specific needs

version: '3.8'

services:
  api:
    environment:
      DEBUG: "true"
      LOG_LEVEL: DEBUG
      RELOAD: "true"
    ports:
      - "8000:8000"

  postgres:
    environment:
      POSTGRES_INITDB_ARGS: "-c log_statement=all -c log_min_duration_statement=0"
    ports:
      - "5432:5432"
```

### Local Development Commands

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Run database migrations
docker-compose exec api poetry run alembic upgrade head

# Load seed data
docker-compose exec api python scripts/seed.py

# View logs
docker-compose logs -f api

# Run tests
docker-compose exec api poetry run pytest

# Stop services
docker-compose down

# Remove all data (clean slate)
docker-compose down -v
```

### Environment Variables (.env.example)

```bash
# JWT Configuration
JWT_SECRET_DEV=dev-secret-key-change-in-staging
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=8

# Database (development)
DATABASE_URL=postgresql://archery_user:archery_password@localhost:5432/archery_dev

# Redis (development)
REDIS_URL=redis://localhost:6379/0

# API Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=true

# CORS (development - allows localhost)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Storage
STORAGE_PATH=/storage
STORAGE_QUOTA_GB=10

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# WebSocket
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_GRACE_PERIOD_SECONDS=30

# Image Processing
IMAGE_COMPRESSION_QUALITY=70
IMAGE_MAX_SIZE_MB=5

# Rate Limiting
RATE_LIMIT_PER_MINUTE=1000

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
AUDIT_LOG_TABLE=audit_logs
```

---

## Staging Environment - AWS ECS Deployment

### AWS Infrastructure Setup

#### 1. VPC & Networking

```bash
# Create VPC
aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=archery-staging}]'

# Create public subnet (ALB)
aws ec2 create-subnet \
  --vpc-id vpc-xxxxx \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a

# Create private subnet (RDS, ElastiCache)
aws ec2 create-subnet \
  --vpc-id vpc-xxxxx \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1a
```

#### 2. RDS PostgreSQL Setup

```bash
aws rds create-db-instance \
  --db-instance-identifier archery-staging-db \
  --db-instance-class db.t3.small \
  --engine postgres \
  --engine-version 15.2 \
  --master-username archery_user \
  --master-user-password '$(openssl rand -base64 32)' \
  --allocated-storage 20 \
  --storage-type gp3 \
  --db-name archery_staging \
  --db-subnet-group-name archery-subnet-group \
  --vpc-security-group-ids sg-xxxxx \
  --multi-az false \
  --publicly-accessible false \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --enable-cloudwatch-logs-exports '["postgresql"]' \
  --storage-encrypted true \
  --kms-key-id arn:aws:kms:us-east-1:xxxxx:key/xxxxx
```

#### 3. ElastiCache Redis Setup

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id archery-staging-cache \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --cache-subnet-group-name archery-cache-subnet \
  --vpc-security-group-ids sg-xxxxx \
  --port 6379 \
  --parameter-group-name default.redis7 \
  --auto-failover-enabled false \
  --at-rest-encryption-enabled true \
  --transit-encryption-enabled true \
  --log-delivery-configurations 'LogType=slow-log,DestinationType=cloudwatch-logs,DestinationDetails={CloudWatchLogsLogGroupName=/aws/elasticache/archery-staging}'
```

#### 4. S3 Bucket Setup

```bash
# Create S3 bucket
aws s3api create-bucket \
  --bucket archery-staging-images \
  --region us-east-1 \
  --create-bucket-configuration LocationConstraint=us-east-1

# Enable versioning (optional, for recovery)
aws s3api put-bucket-versioning \
  --bucket archery-staging-images \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket archery-staging-images \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access
aws s3api put-public-access-block \
  --bucket archery-staging-images \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### ECS Cluster & Task Definition

#### 1. Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name archery-staging \
  --cluster-settings name=containerInsights,value=enabled
```

#### 2. ECS Task Definition

**task-definition.json**:

```json
{
  "family": "archery-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["EC2"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "archery-api",
      "image": "{{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com/archery-api:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "staging"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        },
        {
          "name": "PROMETHEUS_ENABLED",
          "value": "true"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:{{AWS_ACCOUNT_ID}}:secret:archery/staging/db-url"
        },
        {
          "name": "REDIS_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:{{AWS_ACCOUNT_ID}}:secret:archery/staging/redis-url"
        },
        {
          "name": "JWT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:{{AWS_ACCOUNT_ID}}:secret:archery/staging/jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/archery-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs",
          "awslogs-datetime-format": "%Y-%m-%d %H:%M:%S"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ],
  "executionRoleArn": "arn:aws:iam::{{AWS_ACCOUNT_ID}}:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::{{AWS_ACCOUNT_ID}}:role/archery-api-task-role"
}
```

#### 3. Register Task Definition

```bash
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json
```

#### 4. Create ECS Service

```bash
aws ecs create-service \
  --cluster archery-staging \
  --service-name archery-api \
  --task-definition archery-api:1 \
  --desired-count 1 \
  --launch-type EC2 \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-xxxxx],
    securityGroups=[sg-xxxxx],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:xxxxx:targetgroup/archery-api/xxxxx,containerName=archery-api,containerPort=8000" \
  --deployment-configuration "maximumPercent=100,minimumHealthyPercent=0"
```

### Application Load Balancer (ALB)

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name archery-staging-alb \
  --subnets subnet-xxxxx \
  --security-groups sg-xxxxx \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4 \
  --tags Key=Environment,Value=staging

# Create target group
aws elbv2 create-target-group \
  --name archery-api-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxx \
  --target-type ip \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# Create listener (HTTPS)
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:xxxxx:loadbalancer/app/archery-staging-alb/xxxxx \
  --protocol HTTPS \
  --port 443 \
  --certificate-arn arn:aws:acm:us-east-1:xxxxx:certificate/xxxxx \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:xxxxx:targetgroup/archery-api-tg/xxxxx

# Redirect HTTP to HTTPS
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:xxxxx:loadbalancer/app/archery-staging-alb/xxxxx \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'
```

### CloudWatch Monitoring

```bash
# Create CloudWatch Log Group
aws logs create-log-group \
  --log-group-name /ecs/archery-api

aws logs put-retention-policy \
  --log-group-name /ecs/archery-api \
  --retention-in-days 7

# Create CloudWatch Alarms
aws cloudwatch put-metric-alarm \
  --alarm-name archery-api-high-latency \
  --alarm-description "Alert when API latency > 500ms" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 0.5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:xxxxx:archery-alerts

aws cloudwatch put-metric-alarm \
  --alarm-name archery-api-error-rate \
  --alarm-description "Alert when error rate > 1%" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:xxxxx:archery-alerts
```

---

## Production Environment - AWS ECS Auto-Scaling

### Infrastructure as Code (Terraform)

**main.tf** (simplified):

```hcl
provider "aws" {
  region = "us-east-1"
}

# VPC
resource "aws_vpc" "archery" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "archery-prod"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.archery.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "archery-public-${count.index + 1}"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.archery.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "archery-private-${count.index + 1}"
  }
}

# ALB
resource "aws_lb" "archery" {
  name               = "archery-prod-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = true

  tags = {
    Name = "archery-prod-alb"
  }
}

# RDS Aurora PostgreSQL
resource "aws_rds_cluster" "archery" {
  cluster_identifier      = "archery-prod"
  engine                  = "aurora-postgresql"
  engine_version          = "15.2"
  database_name           = "archery_prod"
  master_username         = "archery_admin"
  master_password         = random_password.db_password.result
  db_subnet_group_name    = aws_db_subnet_group.archery.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  backup_retention_period = 35
  storage_encrypted       = true

  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = {
    Name = "archery-prod-db"
  }
}

resource "aws_rds_cluster_instance" "archery" {
  count              = 2
  cluster_identifier = aws_rds_cluster.archery.id
  instance_class     = "db.t3.medium"
  engine              = aws_rds_cluster.archery.engine
  engine_version      = aws_rds_cluster.archery.engine_version

  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  tags = {
    Name = "archery-prod-db-${count.index + 1}"
  }
}

# ElastiCache Redis Cluster
resource "aws_elasticache_replication_group" "archery" {
  replication_group_description = "Archery Production Redis Cluster"
  engine                         = "redis"
  engine_version                 = "7.0"
  node_type                      = "cache.r7g.large"
  num_cache_clusters             = 2
  parameter_group_name           = "default.redis7"
  port                           = 6379
  subnet_group_name              = aws_elasticache_subnet_group.archery.name
  security_group_ids             = [aws_security_group.redis.id]
  automatic_failover_enabled      = true
  at_rest_encryption_enabled     = true
  transit_encryption_enabled      = true

  tags = {
    Name = "archery-prod-cache"
  }
}

# S3 Bucket with Intelligent-Tiering
resource "aws_s3_bucket" "archery" {
  bucket = "archery-prod-images-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "archery-prod-images"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "archery" {
  bucket = aws_s3_bucket.archery.id

  rule {
    id     = "intelligent-tiering"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "INTELLIGENT_TIERING"
    }
  }

  rule {
    id     = "delete-old-archives"
    status = "Enabled"

    expiration {
      days = 365
    }
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "archery" {
  name = "archery-prod"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "archery-prod"
  }
}

# Auto Scaling Group (EC2)
resource "aws_autoscaling_group" "archery" {
  name                = "archery-prod-asg"
  vpc_zone_identifier = aws_subnet.private[*].id
  target_group_arns   = [aws_lb_target_group.archery.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = 2
  max_size         = 5
  desired_capacity = 2

  launch_template {
    id      = aws_launch_template.archery.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "archery-prod-ecs"
    propagate_at_launch = true
  }
}

# Scaling Policy
resource "aws_autoscaling_policy" "scale_up" {
  name                   = "archery-scale-up"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  autoscaling_group_name = aws_autoscaling_group.archery.name
  cooldown               = 300
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "archery-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "70"
  alarm_actions       = [aws_autoscaling_policy.scale_up.arn]
}
```

---

## Secrets Management

### AWS Secrets Manager

```bash
# Create database password secret
aws secretsmanager create-secret \
  --name archery/prod/db-url \
  --description "Production database URL" \
  --secret-string "postgresql://archery_admin:PASSWORD@archery-prod.xxxxx.us-east-1.rds.amazonaws.com:5432/archery_prod"

# Create JWT secret
aws secretsmanager create-secret \
  --name archery/prod/jwt-secret \
  --description "JWT signing secret" \
  --secret-string "$(openssl rand -base64 32)" \
  --add-replica-region RegionCode=us-west-2

# Create automatic rotation policy
aws secretsmanager rotate-secret \
  --secret-id archery/prod/jwt-secret \
  --rotation-rules AutomaticallyAfterDays=30
```

### Application Environment Variables

**For ECS Task**:
- `DATABASE_URL`: Retrieved from Secrets Manager
- `REDIS_URL`: Retrieved from Secrets Manager
- `JWT_SECRET`: Retrieved from Secrets Manager
- `ENVIRONMENT`: production
- `LOG_LEVEL`: INFO
- `PROMETHEUS_ENABLED`: true

---

## Health Checks & Monitoring

### Application Health Endpoint

```python
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for load balancer and monitoring.
    Returns 200 if all components are healthy.
    """
    try:
        # Check database
        db.execute("SELECT 1")
        
        # Check Redis
        redis_client.ping()
        
        # Check storage
        storage_path = Path("/storage")
        if not storage_path.exists():
            raise Exception("Storage path not accessible")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": "ok",
                "cache": "ok",
                "storage": "ok"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}, 503
```

### CloudWatch Metrics

**Application Metrics**:
- `api.latency` (ms): Request latency (p50, p95, p99)
- `api.requests_total` (count): Total requests
- `api.errors_total` (count): Total errors
- `api.error_rate` (%): Error percentage
- `scoring.duration_ms` (ms): Scoring pipeline duration
- `image.processing_ms` (ms): Image processing time
- `cache.hit_rate` (%): Cache hit percentage
- `database.connections` (count): Active DB connections
- `storage.usage_gb` (GB): Storage usage

**Infrastructure Metrics**:
- `rds.cpu_utilization` (%): Database CPU
- `rds.database_connections` (count): DB connections
- `elasticache.cpu_utilization` (%): Cache CPU
- `elasticache.evictions` (count): Cache evictions
- `ecs.cpu_utilization` (%): Container CPU
- `ecs.memory_utilization` (%): Container memory

### CloudWatch Alarms

| Alarm | Threshold | Action |
|---|---|---|
| API Latency High | > 500ms | SNS → Slack |
| Error Rate High | > 1% | SNS → PagerDuty |
| Database CPU High | > 80% | SNS → Slack |
| Cache Evictions | > 0 | SNS → alert |
| Storage Quota | > 90% | SNS → alert |
| RDS Replication Lag | > 1s | SNS → page |
| ASG Scaling Events | > 3/hour | SNS → investigate |

---

## Deployment Procedures

### Development Deployment (Local)

```bash
# Clone repository
git clone https://github.com/archery-scoring/backend.git
cd backend

# Copy environment variables
cp .env.example .env
# Edit .env with local settings

# Start services
docker-compose up -d

# Run migrations
docker-compose exec api poetry run alembic upgrade head

# Load seed data (optional)
docker-compose exec api python scripts/seed.py

# Verify health
curl http://localhost:8000/health

# View logs
docker-compose logs -f api
```

### Staging Deployment (AWS)

```bash
# Build and push Docker image
docker build -t {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com/archery-api:latest .
aws ecr get-login-password | docker login --username AWS --password-stdin {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com
docker push {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com/archery-api:latest

# Update ECS service (blue/green deployment)
aws ecs update-service \
  --cluster archery-staging \
  --service archery-api \
  --force-new-deployment

# Monitor deployment
aws ecs describe-services \
  --cluster archery-staging \
  --services archery-api \
  --query 'services[0].deployments'

# Verify health
STAGING_URL=$(aws elbv2 describe-load-balancers --names archery-staging-alb --query 'LoadBalancers[0].DNSName' --output text)
curl https://$STAGING_URL/health
```

### Production Deployment (AWS with Canary)

```bash
# 1. Build and push image
docker build -t {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com/archery-api:v{{VERSION}} .
docker push {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com/archery-api:v{{VERSION}}

# 2. Register new task definition
aws ecs register-task-definition \
  --family archery-api \
  --container-definitions "[{...}]"

# 3. Canary deployment (10% traffic)
aws elbv2 modify-rule \
  --rule-arn arn:aws:elasticloadbalancing:us-east-1:xxxxx:listener-rule/app/archery-prod-alb/xxxxx/rule/xxxxx \
  --conditions Field=path-pattern,Values="/api/*" \
  --actions Type=forward,TargetGroups='[{TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:xxxxx:targetgroup/archery-api-v{{NEW}}/xxxxx,Weight=10},{TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:xxxxx:targetgroup/archery-api-v{{OLD}}/xxxxx,Weight=90}]'

# 4. Monitor canary metrics (5 minutes)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average,Maximum

# 5. If healthy, route remaining traffic
aws elbv2 modify-rule \
  --rule-arn arn:aws:elasticloadbalancing:us-east-1:xxxxx:listener-rule/app/archery-prod-alb/xxxxx/rule/xxxxx \
  --actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:xxxxx:targetgroup/archery-api-v{{NEW}}/xxxxx

# 6. Decommission old task definition
aws ecs deregister-task-definition \
  --task-definition archery-api:{{OLD_REVISION}}
```

---

## Rollback Procedures

### If Deployment Fails

```bash
# Staging: Immediate rollback
aws ecs update-service \
  --cluster archery-staging \
  --service archery-api \
  --task-definition archery-api:{{PREVIOUS_REVISION}}

# Production: Reroute traffic to stable version
aws elbv2 modify-rule \
  --rule-arn arn:aws:elasticloadbalancing:us-east-1:xxxxx:listener-rule/app/archery-prod-alb/xxxxx/rule/xxxxx \
  --actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:xxxxx:targetgroup/archery-api-v{{STABLE}}/xxxxx

# Monitor rollback
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:xxxxx:targetgroup/archery-api/xxxxx

# Post incident review
# - Update incident log
# - Root cause analysis
# - Implement preventive measures
```

---

## Summary

| Aspect | Dev | Staging | Prod |
|---|---|---|---|
| **Deployment Method** | Docker Compose | AWS ECS (manual) | AWS ECS (auto-scaling) |
| **Compute** | Local (1 container) | EC2 (1 instance) | EC2 ASG (2-5 instances) |
| **Database** | PostgreSQL container | RDS (db.t3.small) | Aurora PostgreSQL (db.t3.medium) |
| **Load Balancing** | None (direct:8000) | ALB | Multi-AZ ALB |
| **Monitoring** | Local logs | CloudWatch (basic) | CloudWatch (full) |
| **Deployment Pipeline** | Manual | GitHub Actions → ECS | GitHub Actions → Canary → Prod |
| **Health Checks** | Manual | ALB probes (30s) | ALB probes (30s) + CloudWatch alarms |
| **Cost** | ~$0 | ~$110/month | ~$285/month |

