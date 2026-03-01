# Doc Translation Backend

GraphQL API backend for the Doc Translation System using AWS Bedrock.

## Quick Start

```bash
cd backend
uv sync                    # Install dependencies
cp .env.example .env       # Configure environment
uv run main.py             # Start server
```

Server runs on http://localhost:8000 with GraphQL playground at `/api/graphql`.

## Architecture

```
backend/
├── main.py                         # ASGI application entry point
├── pyproject.toml                  # Dependencies (uv)
└── src/
    ├── core/
    │   └── app_config.py           # Application configuration
    ├── models/
    │   ├── job.py                  # Job data models
    │   ├── config.py               # Config data models
    │   └── legacy_config.py        # LanguagePair, ModelInfo, AWSConfig
    ├── services/
    │   ├── auth_service.py         # JWT authentication
    │   ├── excel_processor.py      # Excel read/write (openpyxl)
    │   ├── translation_service.py  # Bedrock API integration
    │   ├── translation_orchestrator.py  # Job coordination
    │   ├── job_manager.py          # Job lifecycle management
    │   ├── concurrent_executor.py  # Parallel processing
    │   ├── config_service.py       # Configuration service (DynamoDB)
    │   └── global_config_service.py # Global config management
    ├── storage/
    │   ├── s3_file_storage.py      # S3 file upload/download
    │   ├── job_store.py            # In-memory job storage
    │   └── dynamodb_repository.py  # DynamoDB persistence
    └── graphql/
        ├── schema.py               # GraphQL type definitions
        └── resolvers.py            # Query/mutation implementations
```

## Configuration

### Environment Variables (.env)

See `.env.example` for a complete template with comments.

#### Required Variables

| Variable | Description |
|----------|-------------|
| `S3_BUCKET` | AWS S3 bucket name for file storage |
| `JWT_SECRET` | JWT signing key for authentication tokens |

#### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host binding |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable Starlette debug mode |
| `RELOAD` | `false` | Auto-reload on file changes |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MAX_CONCURRENT_FILES` | `5` | Max files to process in parallel |
| `TRANSLATION_BATCH_SIZE` | `10` | Cells/paragraphs per Bedrock API call |
| `MAX_FILE_SIZE` | `52428800` | Max upload file size in bytes (50MB) |
| `FRONTEND_URL` | `http://localhost:3000` | Frontend URL for CORS |

#### AWS Configuration

AWS credentials are typically provided via:
- IAM instance role (recommended for EC2/ECS)
- AWS CLI configuration (`~/.aws/credentials`)
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`)

### Runtime Configuration

Configuration is stored in DynamoDB and managed via the GraphQL API.

### Initial Setup

Create admin user via CLI:

```bash
uv run python -m src.cli.commands create-tables
uv run python -m src.cli.commands create-admin -u admin -p initial-password
```

The admin user must change their password on first login.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `POST /api/graphql` | GraphQL API |
| `GET /api/graphql` | GraphiQL interface |
| `POST /api/upload` | File upload |
| `GET /api/download` | File download |

## GraphQL Examples

### Login

```graphql
mutation {
  login(username: "admin", password: "password") {
    token
    user { username }
  }
}
```

### Create Translation Job

```graphql
mutation {
  createTranslationJob(fileIds: ["id1"], languagePairId: "zh-vi") {
    id
    status
  }
}
```

### Query Job Status

```graphql
query {
  job(id: "job-id") {
    status
    progress
    filesCompleted
    filesTotal
  }
}
```

## Commands

```bash
uv sync                      # Install dependencies
uv sync --extra dev          # Install with dev dependencies
uv run main.py               # Start server
uv run pytest tests/ -v      # Run tests
```

## Key Features

- **JWT Authentication** with bcrypt password hashing
- **Multi-language Support** with configurable language pairs
- **Concurrent Processing** (configurable files × worksheets)
- **Format Preservation** (fonts, colors, borders, images, formulas)
- **Real-time Progress** tracking with job management
- **Error Isolation** - partial failures don't stop other files
- **Retry Logic** with exponential backoff for API calls

---

[Back to main README](../README.md)
