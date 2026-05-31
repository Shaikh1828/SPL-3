# Archery Scoring System - Deployment Guide

## Table of Contents

1. [Development Setup](#development-setup)
2. [Staging Deployment](#staging-deployment)
3. [Production Deployment](#production-deployment)
4. [Database Migrations](#database-migrations)
5. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
6. [Environment Configuration](#environment-configuration)
7. [Backup & Recovery](#backup--recovery)

---

## Development Setup

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Git
- Python 3.11+ (for local development without Docker)
- PostgreSQL 15+ (if not using Docker)
- Redis 7+ (if not using Docker)

### Quick Start (Docker Compose)

**1. Clone Repository**
```bash
git clone <repository-url>
cd SPL-3
```

**2. Configure Environment**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with development settings (or use defaults)
# Default: DATABASE_URL=postgresql://archery:archery_pass@localhost:5432/archery_db
```

**3. Start Services**
```bash
# Build and start all containers (api, postgres, redis)
docker-compose up -d

# Verify all services are running
docker-compose ps
# Expected output:
# - archery_scoring_api     (running on :8000)
# - archery_scoring_db      (running on :5432)
# - archery_scoring_cache   (running on :6379)
```

**4. Access Application**
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **Health Check**: http://localhost:8000/api/health

**5. Seed Database (Automatic)**
Docker Compose runs seed data automatically on first startup:
```bash
# If needed to manually seed:
docker-compose exec api python -m scripts.seed_data
```

**6. View Logs**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f db
docker-compose logs -f cache
```

**7. Stop Services**
```bash
docker-compose down

# Remove volumes (clean database/cache)
docker-compose down -v
```

### Local Development (Without Docker)

**1. Create Virtual Environment**
```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n archery_scoring python=3.11
conda activate archery_scoring
```

**2. Install Dependencies**
```bash
pip install poetry
poetry install
```

**3. Start External Services (Docker only)**
```bash
# Start only database and cache
docker-compose up -d db cache
```

**4. Initialize Database**
```bash
# Run migrations
alembic upgrade head

# Seed data
python -m scripts.seed_data
```

**5. Run Application**
```bash
# Development with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or with 4 workers
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**6. Run Tests**
```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_api_endpoints.py -v

# Only integration tests
pytest -m integration

# Only unit tests
pytest -m unit
```

---

## Staging Deployment

### AWS ECS (Single Container - t3.medium)

**1. Build and Push Docker Image**
```bash
# Configure AWS credentials
export AWS_PROFILE=staging

# Build image
docker build -t archery-scoring-api:latest .

# Tag for ECR
aws ecr describe-repositories --region us-east-1 \
  --query 'repositories[0].repositoryUri' --output text
# Output: 123456789.dkr.ecr.us-east-1.amazonaws.com/archery-scoring-api

# Tag and push
docker tag archery-scoring-api:latest \
  123456789.dkr.ecr.us-east-1.amazonaws.com/archery-scoring-api:staging
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/archery-scoring-api:staging
```

**2. Create RDS PostgreSQL Instance**
```bash
aws rds create-db-instance \
  --db-instance-identifier archery-scoring-staging \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username archery \
  --master-user-password <STRONG_PASSWORD> \
  --allocated-storage 20 \
  --storage-type gp3 \
  --multi-az \
  --backup-retention-period 7 \
  --region us-east-1

# Wait for instance to be available (~10 minutes)
aws rds describe-db-instances --db-instance-identifier archery-scoring-staging \
  --region us-east-1 --query 'DBInstances[0].DBInstanceStatus'
```

**3. Create ElastiCache Redis Cluster**
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id archery-scoring-staging \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --security-group-ids sg-xxxxxxxx \
  --region us-east-1

# Wait for cluster to be available (~5 minutes)
aws elasticache describe-cache-clusters \
  --cache-cluster-id archery-scoring-staging \
  --show-cache-node-info --region us-east-1
```

**4. Create ECS Cluster and Task Definition**
```bash
# Create cluster
aws ecs create-cluster --cluster-name archery-scoring-staging --region us-east-1

# Create task definition (use task-definition.json)
aws ecs register-task-definition \
  --cli-input-json file://task-definition-staging.json \
  --region us-east-1
```

**5. Create ECS Service**
```bash
aws ecs create-service \
  --cluster archery-scoring-staging \
  --service-name api \
  --task-definition archery-scoring-api:1 \
  --desired-count 1 \
  --launch-type EC2 \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=api,containerPort=8000 \
  --region us-east-1
```

**6. Run Database Migrations**
```bash
# SSH into container and run migrations
aws ecs execute-command \
  --cluster archery-scoring-staging \
  --task-id <TASK_ID> \
  --container api \
  --interactive \
  --command "alembic upgrade head"
```

**7. Verify Deployment**
```bash
# Check service status
aws ecs describe-services \
  --cluster archery-scoring-staging \
  --services api \
  --region us-east-1

# Get ALB endpoint
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[0].DNSName' \
  --region us-east-1

# Test health endpoint
curl https://<ALB_DNS>/api/health
```

---

## Production Deployment

### AWS ECS Auto-Scaling (2-5 t3.medium instances)

**1. Configure Auto-Scaling Target**
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/archery-scoring-production/api \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 5 \
  --region us-east-1

# CPU-based scaling policy (target 70% CPU)
aws application-autoscaling put-scaling-policy \
  --policy-name cpu-scaling \
  --service-namespace ecs \
  --resource-id service/archery-scoring-production/api \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }' \
  --region us-east-1
```

**2. Set Up Load Balancer (ALB)**
```bash
# Create Application Load Balancer
aws elbv2 create-load-balancer \
  --name archery-scoring-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxx \
  --scheme internet-facing \
  --type application \
  --region us-east-1

# Create target group
aws elbv2 create-target-group \
  --name archery-scoring-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxx \
  --health-check-path /api/health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --region us-east-1

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:... \
  --region us-east-1
```

**3. Configure RDS for Production (Multi-AZ, Backup)**
```bash
# Create Multi-AZ RDS instance
aws rds create-db-instance \
  --db-instance-identifier archery-scoring-production \
  --db-instance-class db.t3.small \
  --engine postgres \
  --engine-version 15.4 \
  --master-username archery \
  --master-user-password <VERY_STRONG_PASSWORD> \
  --allocated-storage 100 \
  --storage-type gp3 \
  --iops 3000 \
  --multi-az \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --region us-east-1

# Enable automated backup
aws rds modify-db-instance \
  --db-instance-identifier archery-scoring-production \
  --backup-retention-period 30 \
  --copy-tags-to-snapshot \
  --region us-east-1 \
  --apply-immediately
```

**4. Configure ElastiCache Redis Cluster (Multi-AZ, Replication)**
```bash
# Create replication group (with automatic failover)
aws elasticache create-replication-group \
  --replication-group-id archery-scoring-production \
  --replication-group-description "Production cache for archery scoring" \
  --cache-node-type cache.t3.small \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --port 6379 \
  --security-group-ids sg-xxxxx \
  --region us-east-1

# Enable automatic backup
aws elasticache modify-replication-group \
  --replication-group-id archery-scoring-production \
  --snapshot-retention-limit 7 \
  --region us-east-1
```

**5. Deploy Production Image**
```bash
# Update task definition with production settings
aws ecs register-task-definition \
  --cli-input-json file://task-definition-production.json \
  --region us-east-1

# Update service with new task definition
aws ecs update-service \
  --cluster archery-scoring-production \
  --service api \
  --task-definition archery-scoring-api:production \
  --desired-count 2 \
  --force-new-deployment \
  --region us-east-1

# Wait for deployment
aws ecs wait services-stable \
  --cluster archery-scoring-production \
  --services api \
  --region us-east-1
```

**6. Set Up Monitoring & Alerts**
```bash
# CloudWatch Dashboard
aws cloudwatch put-dashboard \
  --dashboard-name archery-scoring-production \
  --dashboard-body file://dashboard-config.json \
  --region us-east-1

# Create CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name archery-scoring-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts \
  --region us-east-1
```

---

## Database Migrations

### Using Alembic

**1. Initialize Alembic (Already Done)**
```bash
# Already configured in repository
# alembic init alembic
```

**2. Create a New Migration**
```bash
# Auto-detect schema changes
alembic revision --autogenerate -m "add new column to users"

# Or create empty migration
alembic revision -m "custom migration name"
```

**3. Review and Edit Migration**
```bash
# Edit alembic/versions/xxx_migration_name.py
# Verify upgrade() and downgrade() functions
```

**4. Apply Migration (Upgrade)**
```bash
# Apply to latest version
alembic upgrade head

# Apply N migrations
alembic upgrade +2

# Apply specific version
alembic upgrade b9c1eec88240
```

**5. Rollback Migration (Downgrade)**
```bash
# Downgrade to previous version
alembic downgrade -1

# Downgrade N migrations
alembic downgrade -2

# Downgrade to specific version
alembic downgrade 87412c2e611c
```

**6. Check Migration Status**
```bash
# Show current revision
alembic current

# Show history
alembic history --verbose

# Show pending migrations
alembic heads
```

**7. Migrate in Docker**
```bash
# Run migrations in existing container
docker-compose exec api alembic upgrade head

# Or create one-off container
docker-compose run --rm api alembic upgrade head
```

### Production Migration Strategy

**Before Migrating:**
1. Create backup: `pg_dump archery_db > backup.sql`
2. Test migration in staging environment first
3. Schedule during low-traffic window
4. Have rollback plan ready

**During Migration:**
```bash
# 1. Stop API services (or run in read-only mode)
aws ecs update-service --cluster archery-scoring-production \
  --service api --desired-count 0

# 2. Run migration
aws ecs execute-command \
  --cluster archery-scoring-production \
  --task-id <TASK_ID> \
  --container api \
  --command "alembic upgrade head"

# 3. Restart API services
aws ecs update-service --cluster archery-scoring-production \
  --service api --desired-count 2
```

**If Rollback Needed:**
```bash
# Stop API
aws ecs update-service --cluster archery-scoring-production \
  --service api --desired-count 0

# Rollback database
aws ecs execute-command \
  --cluster archery-scoring-production \
  --task-id <TASK_ID> \
  --container api \
  --command "alembic downgrade -1"

# Restart API
aws ecs update-service --cluster archery-scoring-production \
  --service api --desired-count 2
```

---

## Monitoring & Troubleshooting

### Health Check Endpoints

**Basic Health:**
```bash
curl http://localhost:8000/api/health
# Response: {"status": "healthy", "timestamp": "...", "environment": "development"}
```

**Detailed Component Health:**
```bash
curl http://localhost:8000/api/health/detailed
# Shows: database, cache, storage, threadpool status
```

### Logs

**Docker Logs:**
```bash
# All containers
docker-compose logs -f

# Specific container
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail 100

# Follow with timestamps
docker-compose logs -f --timestamps
```

**CloudWatch Logs (Production):**
```bash
# Stream logs
aws logs tail /ecs/archery-scoring-api --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /ecs/archery-scoring-api \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s)*1000-3600000)) \
  --region us-east-1
```

### Common Issues

**Database Connection Refused**
```bash
# Check PostgreSQL container
docker-compose ps db

# Verify DATABASE_URL in .env
cat .env | grep DATABASE_URL

# Test connection
docker-compose exec api psql $DATABASE_URL -c "SELECT 1"
```

**Redis Connection Failed**
```bash
# Check Redis container
docker-compose ps cache

# Test connection
docker-compose exec api redis-cli -h cache ping

# Verify REDIS_URL
cat .env | grep REDIS_URL
```

**Rate Limiting (429 Errors)**
```bash
# Check your request rate
# Limit: 1000 requests/minute per IP

# Reset rate limit (development)
curl -X POST http://localhost:8000/api/internal/reset-rate-limits
```

**Out of Memory (OOMKilled)**
```bash
# Increase container memory in docker-compose.yml
# Update memory limit in service definition

# Or update ECS task definition in production
# Increase memory reservation / limit
```

**Slow Leaderboard Queries**
```bash
# Check Redis cache
docker-compose exec cache redis-cli INFO stats

# Verify cache is working
docker-compose exec api python -c "
import redis
r = redis.Redis(host='cache', port=6379)
print(r.get('leaderboard:1'))  # Get cached leaderboard
"
```

### Performance Tuning

**Database Pool Sizing:**
```python
# In src/database.py
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,           # Increase if many concurrent connections
    max_overflow=10,        # Additional connections when pool full
    pool_timeout=30,        # Wait 30s for available connection
    pool_recycle=3600,      # Recycle after 1 hour
    pool_pre_ping=True      # Test connection before use
)
```

**Redis Memory:**
```bash
# Check usage
docker-compose exec cache redis-cli INFO memory

# Set max memory policy
docker-compose exec cache redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

**API Workers:**
```bash
# In docker-compose.yml or .env
API_WORKERS=4  # Increase for high concurrency
# Calculate: 2 × CPU_cores + 1 (e.g., 4-core = 9 workers max)
```

---

## Environment Configuration

### Development (.env)
```
ENVIRONMENT=development
DATABASE_URL=postgresql://archery:archery_pass@localhost:5432/archery_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=dev-secret-key-change-in-production
API_WORKERS=2
LOG_LEVEL=DEBUG
DEBUG=True
```

### Staging (.env.staging)
```
ENVIRONMENT=staging
DATABASE_URL=postgresql://archery:${DB_PASSWORD}@archery-staging.rds.amazonaws.com:5432/archery_db
REDIS_URL=redis://archery-staging.cache.amazonaws.com:6379/0
JWT_SECRET=${JWT_SECRET_STAGING}
API_WORKERS=4
LOG_LEVEL=INFO
DEBUG=False
```

### Production (.env.production)
```
ENVIRONMENT=production
DATABASE_URL=postgresql://archery:${DB_PASSWORD}@archery-production.rds.amazonaws.com:5432/archery_db
REDIS_URL=redis://archery-production.cache.amazonaws.com:6379/0
JWT_SECRET=${JWT_SECRET_PRODUCTION}
API_WORKERS=8
LOG_LEVEL=WARNING
DEBUG=False
```

### Secrets Management

**Development:**
- Store in .env (not committed to git)

**AWS Production:**
```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name archery-scoring-secrets \
  --secret-string '{
    "DATABASE_URL": "postgresql://...",
    "JWT_SECRET": "...",
    "REDIS_URL": "redis://..."
  }' \
  --region us-east-1

# Reference in ECS task definition
# valueFrom: arn:aws:secretsmanager:...
```

---

## Backup & Recovery

### Database Backup

**Manual Backup:**
```bash
# Development
docker-compose exec db pg_dump archery_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Production (RDS)
aws rds create-db-snapshot \
  --db-instance-identifier archery-scoring-production \
  --db-snapshot-identifier archery-snapshot-$(date +%Y%m%d-%H%M%S) \
  --region us-east-1
```

**Automatic Backup:**
- RDS handles automatic backups (retention: 7 days staging, 30 days production)
- Point-in-time recovery enabled

**Restore from Backup:**
```bash
# Development
docker-compose down -v  # Remove volumes
docker-compose up -d
cat backup.sql | docker-compose exec -T db psql -U archery -d archery_db

# Production
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier archery-scoring-restored \
  --db-snapshot-identifier archery-snapshot-20260525-120000 \
  --region us-east-1
```

### Storage Backup

**Local Development:**
```bash
# Backup /storage directory
tar -czf storage_backup_$(date +%Y%m%d).tar.gz ./storage/
```

**Production (S3):**
```bash
# Archive old images (90+ days)
docker-compose exec api python -c "
from src.utils.storage import StorageManager
sm = StorageManager()
success, count = sm.archive_old_images(days=90)
print(f'Archived {count} images')
"

# Upload to S3
aws s3 sync ./storage/archives s3://archery-scoring-backups/
```

---

## Deployment Checklist

### Before Deployment

- [ ] All tests pass: `pytest`
- [ ] Test coverage > 70%: `pytest --cov=src`
- [ ] Code review complete
- [ ] Database migrations reviewed and tested
- [ ] Environment variables configured
- [ ] Secrets stored securely
- [ ] Staging deployment verified
- [ ] Load testing completed
- [ ] Backup created
- [ ] Rollback plan documented

### During Deployment

- [ ] Monitoring dashboard open
- [ ] On-call engineer available
- [ ] Communication channel open (Slack/Teams)
- [ ] Deploy to staging first
- [ ] Run smoke tests
- [ ] Deploy to production
- [ ] Monitor error rates and latency
- [ ] Verify health checks passing

### After Deployment

- [ ] All health checks green
- [ ] Error rate < 0.1%
- [ ] P99 latency < 1000ms
- [ ] Database connections healthy
- [ ] Cache hit rate > 80%
- [ ] Monitor for 1 hour minimum
- [ ] Document deployment in log
- [ ] Notify stakeholders

---

## Support & Escalation

**Issues:**
- Development: Check logs with `docker-compose logs -f api`
- Staging: Check CloudWatch logs
- Production: Page on-call engineer

**Escalation Path:**
1. Check health endpoints
2. Review recent logs for errors
3. Check AWS CloudWatch alarms
4. Verify database connectivity
5. Check cache connectivity
6. Review recent code changes
7. Consider rollback if necessary
