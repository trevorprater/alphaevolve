# AlphaEvolve Production Deployment Guide

This guide covers deploying AlphaEvolve in production environments with best practices for security, reliability, and performance.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Security Hardening](#security-hardening)
- [Deployment Options](#deployment-options)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Recovery](#backup-and-recovery)
- [Performance Tuning](#performance-tuning)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Python**: 3.12 or newer
- **OS**: Linux (Ubuntu 22.04+ or RHEL 8+), macOS, or Windows
- **Memory**: Minimum 4GB RAM (8GB+ recommended)
- **CPU**: 2+ cores recommended
- **Disk**: 10GB+ free space
- **Docker**: 24.0+ (for sandbox isolation)

### External Services

- **LLM Provider Account**: At least one of:
  - OpenAI API account
  - Anthropic API account
  - Google Cloud account (for Vertex AI)
  - Google AI Studio account (for Gemini API)

### Network Requirements

- Outbound HTTPS (443) to LLM provider APIs
- Inbound access (if running as a service)
- Docker registry access (if using containers)

## Installation

### Option 1: Using pip/uv (Recommended)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install AlphaEvolve
pip install alphaevolve

# Or with uv (faster)
uv pip install alphaevolve

# Install with all optional dependencies
uv pip install 'alphaevolve[all]'
```

### Option 2: From Source

```bash
# Clone repository
git clone https://github.com/your-username/alphaevolve.git
cd alphaevolve

# Install in production mode
uv pip install -e ".[llm]"
```

### Option 3: Docker

```bash
# Pull official image
docker pull ghcr.io/your-username/alphaevolve:latest

# Or build from source
docker build -t alphaevolve:latest .
```

## Configuration

### Environment Variables

Create a `.env` file in your deployment directory:

```bash
# Copy example
cp .env.example .env

# Edit with production values
nano .env
```

**Required Variables:**

```bash
# Primary LLM Provider
ANTHROPIC_API_KEY=sk-ant-xxxxx  # Or your provider's key

# For Google Cloud/Vertex AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

**Optional Variables:**

```bash
# Environment
ALPHAEVOLVE_ENV=production

# Logging
LOG_LEVEL=INFO

# Metrics
ENABLE_METRICS=true
```

### Configuration File

Create `alphaevolve.yaml` for production:

```yaml
# Production configuration
project_name: "AlphaEvolve Production"
environment: "production"

# LLM Configuration
llm:
  default_provider: "anthropic"
  fallback_provider: "openai"

  providers:
    anthropic:
      api_key: "${ANTHROPIC_API_KEY}"
      model: "claude-sonnet-4"
      temperature: 0.2
      max_tokens: 2000
      timeout_seconds: 60
      rate_limit_rpm: 50
      use_thinking: true

    openai:
      api_key: "${OPENAI_API_KEY}"
      model: "o1-mini"
      temperature: 0.2
      max_tokens: 2000
      timeout_seconds: 60
      rate_limit_rpm: 60

# Sandbox Configuration (CRITICAL FOR SECURITY)
sandbox:
  enabled: true
  type: "docker"  # Use Docker in production

  cpu_limit: 2.0
  memory_limit: "512m"
  timeout_seconds: 60
  network_disabled: true

  docker_image: "alphaevolve-sandbox:latest"
  docker_pull_policy: "always"

# Security
security:
  strict_sandbox: true
  encrypt_credentials: false

  allowed_imports:
    - "math"
    - "random"
    - "json"
    - "datetime"

  blocked_functions:
    - "exec"
    - "eval"
    - "compile"
    - "__import__"
    - "open"

# Logging
logging:
  level: "INFO"
  file_enabled: true
  file_path: "/var/log/alphaevolve/alphaevolve.log"
  file_max_size: "50MB"
  file_backup_count: 10

  console_enabled: true
  console_level: "WARNING"

# Database/Storage
database:
  checkpoint_interval: 100
  auto_save: true

# Evolution
evolution:
  population_size: 100
  max_generations: 1000
  parallel_evaluations: 4
```

### File Permissions

Secure sensitive files:

```bash
# Restrict .env access
chmod 600 .env

# Restrict config file access
chmod 600 alphaevolve.yaml

# Create log directory
sudo mkdir -p /var/log/alphaevolve
sudo chown $USER:$USER /var/log/alphaevolve
chmod 750 /var/log/alphaevolve
```

## Security Hardening

### 1. API Key Management

**Best Practices:**
- Never commit API keys to version control
- Use environment variables or secret management services
- Rotate keys regularly (quarterly minimum)
- Use separate keys for dev/staging/production
- Set up billing alerts with LLM providers

**Secret Management Options:**
```bash
# AWS Secrets Manager
export ANTHROPIC_API_KEY=$(aws secretsmanager get-secret-value --secret-id prod/alphaevolve/anthropic-key --query SecretString --output text)

# HashiCorp Vault
export ANTHROPIC_API_KEY=$(vault kv get -field=api_key secret/alphaevolve/anthropic)

# Google Secret Manager
export ANTHROPIC_API_KEY=$(gcloud secrets versions access latest --secret="anthropic-api-key")
```

### 2. Sandbox Configuration

**Docker Sandbox (Recommended):**

Build secure sandbox image:

```dockerfile
# Dockerfile.sandbox
FROM python:3.12-slim

RUN useradd -m -u 1000 sandbox
USER sandbox
WORKDIR /workspace

# Install minimal required packages
RUN pip install --no-cache-dir numpy pandas

CMD ["python"]
```

Build and tag:
```bash
docker build -f Dockerfile.sandbox -t alphaevolve-sandbox:latest .
```

**Process Sandbox (Fallback):**
- Disable if Docker available
- Use only for development
- Not recommended for production

### 3. Network Security

**Firewall Rules:**
```bash
# Allow only outbound HTTPS
sudo ufw allow out 443/tcp

# Deny all other outbound by default
sudo ufw default deny outgoing
```

**Docker Network Isolation:**
```bash
# Create isolated network
docker network create --internal alphaevolve-net
```

### 4. Resource Limits

**System-wide limits** (`/etc/security/limits.conf`):
```
alphaevolve soft nofile 4096
alphaevolve hard nofile 8192
alphaevolve soft nproc 256
alphaevolve hard nproc 512
```

**Docker resource limits:**
```yaml
# docker-compose.yml
services:
  alphaevolve:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

## Deployment Options

### Option 1: Systemd Service (Linux)

Create `/etc/systemd/system/alphaevolve.service`:

```ini
[Unit]
Description=AlphaEvolve Evolution Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=alphaevolve
Group=alphaevolve
WorkingDirectory=/opt/alphaevolve
Environment="PATH=/opt/alphaevolve/venv/bin"
EnvironmentFile=/opt/alphaevolve/.env
ExecStart=/opt/alphaevolve/venv/bin/alphaevolve evolve --config /opt/alphaevolve/alphaevolve.yaml
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/alphaevolve/stdout.log
StandardError=append:/var/log/alphaevolve/stderr.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/alphaevolve /opt/alphaevolve/data

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable alphaevolve
sudo systemctl start alphaevolve
sudo systemctl status alphaevolve
```

### Option 2: Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  alphaevolve:
    image: ghcr.io/your-username/alphaevolve:latest
    container_name: alphaevolve
    restart: unless-stopped

    env_file:
      - .env

    volumes:
      - ./alphaevolve.yaml:/app/alphaevolve.yaml:ro
      - ./data:/app/data
      - ./logs:/app/logs
      - /var/run/docker.sock:/var/run/docker.sock  # For Docker sandbox

    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

    networks:
      - alphaevolve-net

    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  alphaevolve-net:
    driver: bridge
```

Deploy:
```bash
docker-compose up -d
docker-compose logs -f
```

### Option 3: Kubernetes

See `k8s/` directory for Kubernetes manifests (coming soon).

## Monitoring and Logging

### Application Logs

**Log Locations:**
- Application log: `/var/log/alphaevolve/alphaevolve.log`
- Stdout log: `/var/log/alphaevolve/stdout.log`
- Stderr log: `/var/log/alphaevolve/stderr.log`

**Log Rotation:**

Configure logrotate (`/etc/logrotate.d/alphaevolve`):
```
/var/log/alphaevolve/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 alphaevolve alphaevolve
    sharedscripts
    postrotate
        systemctl reload alphaevolve
    endscript
}
```

### Metrics and Monitoring

**Prometheus Integration (Optional):**

```yaml
# alphaevolve.yaml
logging:
  metrics_enabled: true
  metrics_port: 8000
```

Prometheus scrape config:
```yaml
scrape_configs:
  - job_name: 'alphaevolve'
    static_configs:
      - targets: ['localhost:8000']
```

**Health Checks:**

```bash
# Check service status
systemctl status alphaevolve

# Check logs for errors
journalctl -u alphaevolve -n 100 --no-pager

# Monitor resource usage
docker stats alphaevolve
```

### Alerting

**Key Metrics to Monitor:**
- API rate limit errors
- Evaluation failures
- Sandbox timeouts
- Memory usage
- Evolution progress

## Backup and Recovery

### Data Backup

**Backup Strategy:**

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/alphaevolve"
DATE=$(date +%Y%m%d-%H%M%S)

# Backup data
tar -czf "$BACKUP_DIR/data-$DATE.tar.gz" /opt/alphaevolve/data

# Backup configuration
cp /opt/alphaevolve/alphaevolve.yaml "$BACKUP_DIR/config-$DATE.yaml"

# Keep only last 30 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

Schedule with cron:
```bash
# Daily backup at 2 AM
0 2 * * * /opt/alphaevolve/backup.sh
```

### Checkpoint Management

AlphaEvolve automatically creates checkpoints. To resume:

```bash
# List checkpoints
alphaevolve checkpoint list

# Resume from checkpoint
alphaevolve checkpoint resume --checkpoint /path/to/checkpoint

# Clean old checkpoints (keep last 5)
alphaevolve checkpoint clean --keep 5
```

## Performance Tuning

### Parallel Evaluation

```yaml
evolution:
  parallel_evaluations: 8  # Adjust based on CPU cores
  batch_evaluation: true
```

### Fitness Approximation

```yaml
evaluation:
  use_approximation: true
  cache_size: 10000
  enable_surrogate: true
```

### Resource Optimization

```yaml
sandbox:
  cpu_limit: 2.0
  memory_limit: "512m"
  timeout_seconds: 30
```

### Database Tuning

```yaml
database:
  batch_size: 100
  checkpoint_interval: 100
  auto_save: true
```

## Troubleshooting

### Common Issues

**1. Import errors / Module not found**
```bash
# Reinstall dependencies
uv pip install -e ".[llm]"
```

**2. Docker permission errors**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**3. API rate limiting**
```yaml
# Reduce rate in config
llm:
  providers:
    anthropic:
      rate_limit_rpm: 30
```

**4. Out of memory**
```yaml
# Reduce resource usage
sandbox:
  memory_limit: "256m"
evolution:
  parallel_evaluations: 2
```

**5. Checkpoint corruption**
```bash
# Resume from earlier checkpoint
alphaevolve checkpoint list
alphaevolve checkpoint resume --checkpoint earlier_checkpoint.pkl
```

### Debug Mode

Enable verbose logging:
```bash
export LOG_LEVEL=DEBUG
alphaevolve evolve --verbose
```

### Support

- GitHub Issues: https://github.com/your-username/alphaevolve/issues
- Documentation: https://github.com/your-username/alphaevolve/tree/main/docs
- Security: See [SECURITY.md](SECURITY.md)

## Production Checklist

Before going live:

- [ ] API keys securely stored (not in code)
- [ ] Docker sandbox enabled and tested
- [ ] Resource limits configured
- [ ] Logging configured and tested
- [ ] Monitoring/alerting set up
- [ ] Backup strategy implemented
- [ ] Security hardening applied
- [ ] Performance tuning completed
- [ ] Documentation reviewed
- [ ] Disaster recovery plan in place
- [ ] Team trained on operations

## Updates and Maintenance

### Updating AlphaEvolve

```bash
# Backup current installation
./backup.sh

# Update package
uv pip install --upgrade alphaevolve

# Restart service
sudo systemctl restart alphaevolve

# Verify
alphaevolve status
```

### Security Updates

Subscribe to security advisories:
- GitHub security alerts
- Project releases
- Security mailing list

Apply security patches promptly.

---

For more information, see the [main documentation](docs/index.md).
