# Docker Setup Guide

This guide explains how to run Open Deep Research using Docker, making it easy to deploy anywhere.

## Prerequisites

- Docker Engine 20.10+ or Docker Desktop
- Docker Compose 2.0+ (optional, for docker-compose.yml)

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd open_deep_research_tavily
   ```

2. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start the service:**
   ```bash
   docker-compose up -d
   ```

4. **Check logs:**
   ```bash
   docker-compose logs -f
   ```

5. **Access the API:**
   - API: http://localhost:8000
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/docs

### Option 2: Using Docker directly

1. **Build the image:**
   ```bash
   docker build -t open-deep-research .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name open-deep-research-api \
     -p 8000:8000 \
     -e OPENAI_API_KEY=your-key-here \
     -e TAVILY_API_KEY=your-key-here \
     open-deep-research
   ```

3. **Or with environment file:**
   ```bash
   docker run -d \
     --name open-deep-research-api \
     -p 8000:8000 \
     --env-file .env \
     open-deep-research
   ```

## Configuration

### Environment Variables

The following environment variables can be set:

**Required (at least one API key):**
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `TAVILY_API_KEY` - Tavily search API key

**Optional API Keys:**
- `GOOGLE_API_KEY` - Google API key
- `GROQ_API_KEY` - Groq API key
- `DEEPSEEK_API_KEY` - DeepSeek API key

**Optional Configuration:**
- `OPENAI_API_BASE_URL` - Custom OpenAI API base URL
- `ANTHROPIC_API_BASE_URL` - Custom Anthropic API base URL
- `PORT` - Server port (default: 8000)
- `LANGSMITH_API_KEY` - LangSmith API key for tracing
- `LANGSMITH_PROJECT` - LangSmith project name
- `LANGSMITH_TRACING` - Enable LangSmith tracing (true/false)
- `SUPABASE_URL` - Supabase URL for authentication
- `SUPABASE_KEY` - Supabase API key

### Using .env file

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-your-key-here
TAVILY_API_KEY=tvly-your-key-here
PORT=8000
```

The docker-compose.yml will automatically load this file.

## Docker Compose Options

### Change Port

Edit `docker-compose.yml` or set environment variable:

```bash
PORT=8080 docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f fastapi-research
```

### Stop the Service

```bash
docker-compose down
```

### Restart the Service

```bash
docker-compose restart
```

### Update and Rebuild

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Usage Examples

### Health Check

```bash
curl http://localhost:8000/health
```

### Research Request

```bash
curl -X POST http://localhost:8000/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What are the latest developments in AI?"}
    ]
  }'
```

### Streaming Research

```bash
curl -X POST http://localhost:8000/v1/research/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Research quantum computing"}
    ]
  }'
```

## Integration with OpenWebUI

When running in Docker, configure OpenWebUI to connect to:

```
FASTAPI_BASE_URL: http://fastapi-research:8000
```

If OpenWebUI is in the same docker-compose.yml, they'll be on the same network.

If OpenWebUI is on the host machine:
- Mac/Windows: `http://host.docker.internal:8000`
- Linux: Use your host IP address

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs fastapi-research
```

### Port already in use

Change the port in docker-compose.yml:
```yaml
ports:
  - "8080:8000"  # Use port 8080 instead
```

### API keys not working

Verify environment variables:
```bash
docker-compose exec fastapi-research env | grep API_KEY
```

### Health check failing

Check if the service is running:
```bash
docker-compose ps
docker-compose exec fastapi-research curl http://localhost:8000/health
```

## Production Deployment

For production, consider:

1. **Use environment variables** instead of .env file
2. **Set up reverse proxy** (nginx, traefik) for SSL
3. **Use Docker secrets** for sensitive data
4. **Set resource limits** in docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
   ```

5. **Enable logging** to external service
6. **Use Docker volumes** for persistent data if needed

## Building for Different Platforms

### Build for ARM64 (Apple Silicon, Raspberry Pi)

```bash
docker buildx build --platform linux/arm64 -t open-deep-research:arm64 .
```

### Build for AMD64

```bash
docker buildx build --platform linux/amd64 -t open-deep-research:amd64 .
```

## Multi-Architecture Build

```bash
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t open-deep-research:latest --push .
```

