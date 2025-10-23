import redis
import click
import uvicorn

from src.core.config import settings
from src.core.logger import log


@click.group()
@click.version_option()
def cli():
    """Speaker Diarization API CLI"""
    pass


@cli.command()
@click.option("--host", default=settings.api_host, help="Host to bind to")
@click.option("--port", default=settings.api_port, help="Port to bind to")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def start(host: str, port: int, debug: bool, reload: bool):
    """Start the FastAPI server"""
    log.info(f"Starting server on {host}:{port}")

    import src.app

    uvicorn.run(
        "src.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="debug" if debug else "info",
    )


@cli.command()
@click.option("--concurrency", default=4, help="Number of worker processes")
@click.option("--loglevel", default="info", help="Log level")
def worker(concurrency: int, loglevel: str):
    """Start Celery worker"""
    log.info(f"Starting Celery worker with concurrency={concurrency}")

    from src.workers.celery_app import celery_app

    celery_app.worker_main(
        [
            "worker",
            f"--loglevel={loglevel}",
            f"--concurrency={concurrency}",
            "--queues=diarization",
        ]
    )


@cli.command()
def init_storage():
    """Initialize storage directories"""
    log.info("Initializing storage directories...")

    # Create storage directories
    base_path = settings.storage_base_path_obj
    (base_path / "uploads").mkdir(exist_ok=True)
    (base_path / "processed").mkdir(exist_ok=True)
    (base_path / "temp").mkdir(exist_ok=True)

    log.info(f"Storage directories created at: {base_path}")


@cli.command()
def check_external_service():
    """Check connectivity to external services"""
    log.info("Checking external services connectivity...")

    services = []

    def mask_redis_url(url: str) -> str:
        """Mask password in Redis URL for logging"""
        if "@" in url:
            # Split URL to mask credentials
            parts = url.split("@")
            if len(parts) == 2:
                auth_part = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
                if ":" in auth_part:
                    # Has username:password
                    username = auth_part.split(":")[0]
                    return url.replace(f"{username}:{auth_part.split(':')[1]}", f"{username}:***")
                else:
                    # Only has password
                    return url.replace(f":{auth_part}@", ":***@")
        return url

    def test_redis_connection(name: str, url: str) -> tuple[bool, str]:
        """Test Redis connection and return (success, error_message)"""
        try:
            redis_client = redis.from_url(url)
            redis_client.ping()
            log.info(f"✅ {name} connection successful")
            return True, None
        except Exception as e:
            log.error(f"❌ {name} connection failed: {e}")
            return False, str(e)

    # Check Redis (main)
    success, error = test_redis_connection("Redis", settings.redis_url)
    services.append(("Redis", mask_redis_url(settings.redis_url), success, error))

    # Check Celery Broker Redis
    success, error = test_redis_connection("Celery Broker", settings.celery_broker_url)
    services.append(("Celery Broker", mask_redis_url(settings.celery_broker_url), success, error))

    # Check Celery Result Backend Redis
    success, error = test_redis_connection("Celery Result Backend", settings.celery_result_backend)
    services.append(("Celery Result Backend", mask_redis_url(settings.celery_result_backend), success, error))

    # Summary
    all_success = all(status for _, _, status, _ in services)
    total_services = len(services)
    successful_services = sum(1 for _, _, status, _ in services if status)

    if all_success:
        log.info(f"🎉 All {total_services} external services are reachable!")
    else:
        log.warning(f"⚠️  {successful_services}/{total_services} external services are reachable")

        print("\n" + "="*60)
        print("EXTERNAL SERVICES CONNECTIVITY REPORT")
        print("="*60)

        for name, url, status, error in services:
            status_symbol = "✅" if status else "❌"
            print(f"{status_symbol} {name}")
            print(f"   URL: {url}")
            if error:
                print(f"   Error: {error}")
            print()

        print("="*60)


if __name__ == "__main__":
    cli()
