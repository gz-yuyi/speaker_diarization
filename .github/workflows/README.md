# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated CI/CD.

## Workflows

### `docker-build.yml`
Triggers on:
- Push to `main`, `develop` branches
- Pull requests to `main`
- Tags (v*.*.*)

**Actions:**
- Multi-platform build (linux/amd64, linux/arm64)
- Automatic tagging based on branch/tag
- SBOM generation
- Docker layer caching
- Push to Alibaba Cloud Container Registry

## Required Secrets

Set up these repository secrets in GitHub Settings > Secrets and variables > Actions:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `ALIYUN_REGISTRY_USERNAME` | Alibaba Cloud Container Registry username | `your_username` |
| `ALIYUN_REGISTRY_PASSWORD` | Alibaba Cloud Container Registry password | `your_password` |
| `HF_TOKEN` | Hugging Face access token for model download | `hf_xxxxxxxxxxxxxxxxxx` |

## Setup Instructions

1. **Get Hugging Face Token:**
   - Visit https://huggingface.co/settings/tokens
   - Create a token with `read` permissions
   - Add it as `HF_TOKEN` secret

2. **Get Alibaba Cloud Registry Credentials:**
   - Visit Alibaba Cloud Container Registry console
   - Get your username and password
   - Add them as `ALIYUN_REGISTRY_USERNAME` and `ALIYUN_REGISTRY_PASSWORD` secrets

3. **Accept Model License:**
   - Visit https://huggingface.co/pyannote/speaker-diarization-3.1
   - Accept the user agreement with your Hugging Face account

## Image Tagging Strategy

- `main` branch → `:latest` tag
- `develop` branch → `:develop` tag
- Tags like `v1.0.0` → `:1.0.0`, `:1.0`, `:1` tags
- Pull requests → `:pr-{number}` tag

## Deployment

After the workflow successfully builds and pushes the image:

```bash
# Pull the latest image
docker pull crpi-lxfoqbwevmx9mc1q.cn-chengdu.personal.cr.aliyuncs.com/yuyi_tech/speaker_diarization:latest

# Deploy with docker-compose
docker-compose up -d
```

## Security Features

- **Multi-platform builds** for amd64 and arm64
- **SBOM generation** for software supply chain transparency
- **Docker layer caching** for faster builds
- **Secure token management** for model downloads