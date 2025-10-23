# Health Check Script

## Overview

The health check script (`scripts/health_check.py`) provides comprehensive monitoring of external services required for the Speaker Diarization API to function properly.

## Supported Services

- **Redis**: Connection and basic functionality tests
- **Celery Broker**: Redis broker connectivity
- **Celery Backend**: Redis result backend connectivity
- **Storage Directories**: File system accessibility and permissions

## Usage

### Standalone Script

```bash
# Check all services
python scripts/health_check.py

# Check specific service
python scripts/health_check.py --service redis

# Verbose output
python scripts/health_check.py --verbose

# JSON output format
python scripts/health_check.py --format json

# Combined options
python scripts/health_check.py --service redis --verbose --format json
```

### CLI Integration

```bash
# Basic health check (same as standalone script)
uv run python main.py health

# Check specific service
uv run python main.py health --service redis

# Verbose output
uv run python main.py health --verbose

# JSON output
uv run python main.py health --format json

# Simple status check (Redis + Storage only)
uv run python main.py status
```

## Options

| Option | Short | Description | Choices | Default |
|--------|-------|-------------|---------|---------|
| `--service` | `-s` | Service to check | `redis`, `celery_broker`, `celery_backend`, `storage`, `all` | `all` |
| `--verbose` | `-v` | Enable verbose logging | - | `False` |
| `--format` | `-f` | Output format | `text`, `json` | `text` |

## Exit Codes

- `0` - All health checks passed
- `1` - One or more health checks failed

## Output Examples

### Text Output (Normal)

```
🔍 Starting health checks for Speaker Diarization API...

ℹ️  Checking Redis connection...
✅ Redis connection OK (0.003s)
✅ Redis read/write operations OK

ℹ️  Checking Celery Broker (Redis)...
✅ Celery Broker (Redis) connection OK

ℹ️  Checking Celery Backend (Redis)...
✅ Celery Backend (Redis) connection OK

ℹ️  Checking Storage Directories...
✅ Directory uploads is writable
✅ Directory processed is writable
✅ Directory temp is writable

📊 Health Check Summary:
==================================================
✅ REDIS: HEALTHY
   Response time: 0.003s
   Version: 7.0.0
✅ CELERY_BROKER: HEALTHY
✅ CELERY_BACKEND: HEALTHY
✅ STORAGE: HEALTHY
   Base path: ./storage
==================================================
```

### JSON Output

```json
{
  "redis": {
    "status": "healthy",
    "response_time": 0.003,
    "version": "7.0.0",
    "memory_usage": "1.2M",
    "connected_clients": 2
  },
  "celery_broker": {
    "status": "healthy"
  },
  "celery_backend": {
    "status": "healthy"
  },
  "storage": {
    "status": "healthy",
    "base_path": "./storage"
  }
}
```

## Integration with Monitoring

The health check script can be easily integrated with monitoring systems:

### Cron Job

```bash
# Check every 5 minutes and log results
*/5 * * * * /path/to/venv/bin/python /path/to/scripts/health_check.py >> /var/log/health_check.log 2>&1
```

### Prometheus/Metrics

The JSON output format can be parsed by monitoring systems to extract metrics.

### Docker Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python scripts/health_check.py --format json || exit 1
```

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Ensure Redis server is running: `redis-server`
   - Check Redis configuration and network accessibility
   - Verify Redis URL in `.env` file

2. **Storage Directory Issues**
   - Run `uv run python main.py init-storage` to create directories
   - Check file permissions on storage directories
   - Ensure sufficient disk space

3. **Import Errors**
   - Run from project root directory
   - Ensure dependencies are installed: `uv sync`
   - Check Python path configuration

### Debug Mode

Use verbose mode for detailed debugging information:

```bash
python scripts/health_check.py --verbose
```

This will show detailed logs for each check step, making it easier to identify issues.