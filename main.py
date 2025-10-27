import redis
import random
import time
import requests
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
@click.option(
    "--include-completed",
    is_flag=True,
    help="Also remove tasks marked as completed or failed",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show the tasks that would be removed without deleting them",
)
def clear_tasks(include_completed: bool, dry_run: bool):
    """Clear residual task records from Redis"""
    from src.services.task_manager import TaskManager

    task_manager = TaskManager()
    redis_client = task_manager.redis_client

    # Determine which task statuses should be removed
    statuses_to_clear = {"pending", "processing"}
    cleared = []
    skipped = []

    for key in redis_client.scan_iter(match="task:*"):
        key_str = key.decode("utf-8")
        task_id = key_str.split("task:", 1)[-1]
        task_data = redis_client.hgetall(key)

        status = task_data.get(b"status", b"").decode("utf-8") if task_data else ""
        normalized_status = status.lower()

        should_clear = include_completed or normalized_status in statuses_to_clear

        if should_clear:
            cleared.append((task_id, status or "unknown"))
        else:
            skipped.append((task_id, status or "unknown"))

    if not cleared:
        log.info("No matching tasks found to clear in Redis")
        if skipped:
            log.info(
                "Existing tasks left untouched: "
                + ", ".join(f"{tid} ({status})" for tid, status in skipped)
            )
        return

    task_list_str = ", ".join(f"{tid} ({status})" for tid, status in cleared)

    if dry_run:
        log.info(f"Dry run: the following tasks would be removed: {task_list_str}")
        if skipped:
            log.info(
                "Tasks preserved due to status filters: "
                + ", ".join(f"{tid} ({status})" for tid, status in skipped)
            )
        return

    # Confirm deletion interactively to avoid accidental clearing
    if not click.confirm(
        f"Delete {len(cleared)} task(s) from Redis: {task_list_str}?", default=False
    ):
        log.info("Task clearing aborted by user")
        return

    for task_id, _ in cleared:
        task_manager.delete_task(task_id)

    log.info(f"Removed {len(cleared)} task(s) from Redis: {task_list_str}")

    if skipped:
        log.info(
            "Tasks preserved due to status filters: "
            + ", ".join(f"{tid} ({status})" for tid, status in skipped)
        )


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


@cli.command()
@click.option("--api-url", default=f"http://{settings.api_host}:{settings.api_port}", help="API base URL")
def check_service(api_url):
    """Check service functionality by testing audio file upload and processing"""
    import os
    from pathlib import Path

    log.info("Starting service functionality check...")

    # Get audio files from assets directory
    assets_dir = Path("assets")
    if not assets_dir.exists():
        log.error("❌ Assets directory not found")
        return

    # Find audio files
    audio_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.ogg'}
    audio_files = []

    for file_path in assets_dir.iterdir():
        if file_path.suffix.lower() in audio_extensions:
            audio_files.append(file_path)

    if not audio_files:
        log.error("❌ No audio files found in assets directory")
        return

    # Randomly select one audio file
    selected_file = random.choice(audio_files)
    log.info(f"📁 Selected audio file: {selected_file.name}")

    try:
        # Check if API is running
        api_health_url = f"{api_url}/health"
        log.info(f"🔍 Checking API health at: {api_health_url}")

        try:
            health_response = requests.get(api_health_url, timeout=10)
            if health_response.status_code == 200:
                log.info("✅ API health check passed")
            else:
                log.error(f"❌ API health check failed: {health_response.status_code}")
                return
        except requests.exceptions.RequestException as e:
            log.error(f"❌ Unable to connect to API: {e}")
            log.error("   Make sure the API server is running with: python main.py start")
            return

        # Upload audio file
        upload_url = f"{api_url}/api/v1/diarize/upload"
        log.info(f"📤 Uploading audio file to: {upload_url}")

        with open(selected_file, 'rb') as f:
            files = {'audio_file': (selected_file.name, f, 'audio/wav')}
            upload_response = requests.post(upload_url, files=files, timeout=30)

        if upload_response.status_code == 200:
            task_data = upload_response.json()
            task_id = task_data.get('task_id')
            log.info(f"✅ File uploaded successfully, task_id: {task_id}")
        else:
            log.error(f"❌ File upload failed: {upload_response.status_code}")
            log.error(f"   Response: {upload_response.text}")
            return

        # Check task status
        status_url = f"{api_url}/api/v1/diarize/status/{task_id}"
        log.info(f"⏳ Monitoring task status...")

        max_wait_time = 3000  # 5 minutes max wait
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                status_response = requests.get(status_url, timeout=10)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    task_status = status_data.get('status')

                    log.info(f"📊 Task status: {task_status}")

                    if task_status == 'completed':
                        log.info("🎉 Task completed successfully!")

                        # Try to download results
                        download_url = f"{api_url}/api/v1/diarize/download/{task_id}"
                        log.info(f"📥 Downloading results from: {download_url}")

                        download_response = requests.get(download_url, timeout=30)
                        if download_response.status_code == 200:
                            log.info("✅ Results downloaded successfully")
                            log.info(f"📄 Content type: {download_response.headers.get('content-type')}")
                        else:
                            log.warning(f"⚠️ Results download failed: {download_response.status_code}")

                        break
                    elif task_status == 'failed':
                        log.error(f"❌ Task failed: {status_data.get('error', 'Unknown error')}")
                        break
                    else:
                        # Still processing, wait and check again
                        time.sleep(5)
                else:
                    log.error(f"❌ Status check failed: {status_response.status_code}")
                    break
            except requests.exceptions.RequestException as e:
                log.error(f"❌ Status check error: {e}")
                break

        if time.time() - start_time >= max_wait_time:
            log.warning("⏰ Task timeout reached (5 minutes)")

    except Exception as e:
        log.error(f"❌ Service check failed: {e}")
        return

    log.info("🎯 Service functionality check completed!")


@cli.command()
@click.option("--auth-token", required=True, help="Hugging Face access token for downloading the model")
@click.option("--model-name", default=settings.model_name, help="Model name to download")
@click.option("--output-dir", default=settings.model_path, help="Directory to save the model")
def download_model(auth_token: str, model_name: str, output_dir: str):
    """Download Hugging Face model for offline usage"""
    try:
        from huggingface_hub import snapshot_download
        from pathlib import Path

        log.info(f"Starting model download for offline usage...")
        log.info(f"Model: {model_name}")
        log.info(f"Output directory: {output_dir}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Convert model name to valid directory name
        model_dir_name = model_name.replace("/", "--")
        model_dir_path = output_path / model_dir_name

        # Check if model already exists
        if model_dir_path.exists():
            log.info(f"Model directory already exists at: {model_dir_path}")
            if click.confirm("Do you want to re-download the model?"):
                import shutil
                shutil.rmtree(model_dir_path)
            else:
                log.info("Using existing model directory")
                return

        log.info(f"Downloading model {model_name}...")
        log.info("This may take several minutes depending on your internet connection and model size.")

        # Download model using huggingface_hub
        downloaded_path = snapshot_download(
            repo_id=model_name,
            token=auth_token,
            local_dir=model_dir_path,
            local_dir_use_symlinks=False
        )

        log.info(f"✅ Model successfully downloaded to: {downloaded_path}")
        log.info(f"🎉 Model is now available for offline usage!")
        log.info(f"You can now run the service completely offline.")

        # Create a marker file to indicate successful download
        marker_file = model_dir_path / ".downloaded_successfully"
        marker_file.write_text(f"Model: {model_name}\nDownloaded: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        log.info("📝 Created download completion marker")

    except ImportError:
        log.error("❌ huggingface_hub package not found")
        log.error("Please install it with: pip install huggingface_hub")
        return
    except Exception as e:
        log.error(f"❌ Model download failed: {e}")
        log.error("Please check:")
        log.error("1. Your auth token is valid and has access to the model")
        log.error("2. You have accepted the user agreement at: https://huggingface.co/pyannote/speaker-diarization-3.1")
        log.error("3. You have a stable internet connection")
        return


if __name__ == "__main__":
    cli()
