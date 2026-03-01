# Doc Translation System

A web application that translates documents (Excel, Word, PowerPoint, PDF, Text, Markdown) between languages using Amazon Bedrock LLM models while preserving formatting.

## Quick Start

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- AWS credentials with Bedrock access
- Docker (optional)

### Local Development

**Backend:**
```bash
cd backend
cp .env.example .env    # Configure AWS credentials and JWT secret
uv sync
uv run main.py          # http://localhost:8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev             # http://localhost:5173
```

On first run, the backend creates a default `admin` user with a **randomly generated password**. Check the server logs for the temporary credentials:

```
WARNING - Default admin created with temporary password: <random>
WARNING - Change this password immediately! It will not be shown again.
```

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for detailed instructions.

### Docker Compose

```bash
docker compose up --build -d
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

## Deployment

### Docker Compose (Local/Dev)

```bash
docker compose up --build -d
```

### ECS Fargate (Production)

See [ecs/README.md](ecs/README.md) for AWS ECS deployment instructions.

## Architecture

```
Vue 3 Frontend  -->  GraphQL API (Strawberry)  -->  Amazon Bedrock
     |                      |                            |
  Ant Design           Starlette/Uvicorn          LLM Translation
  Apollo Client        Document Processors        (Nova, Claude)
                       DynamoDB Storage
```

### Supported Formats

| Format | Library |
|--------|---------|
| Excel (.xlsx) | openpyxl |
| Word (.docx) | python-docx |
| PowerPoint (.pptx) | python-pptx |
| PDF (.pdf) | PyMuPDF |
| Text (.txt) | Built-in |
| Markdown (.md) | Built-in |

### Supported Models

- Nova 2 Lite
- Claude Sonnet 4.5, Claude Haiku 4.5

## AWS Services

- **Amazon Bedrock** - Translation via Converse API
- **Amazon DynamoDB** - Config, users, thesaurus storage
- **Amazon S3** - File storage (uploads, translated outputs)

## API Endpoints

All endpoints under `/api` prefix:

- `POST /api/upload` - File upload
- `GET /api/download?job_id=&filename=` - File download
- `GET /api/graphql` - GraphQL endpoint (playground available when `DEBUG=true`)
- `GET /api/health` - Health check

## Documentation

For detailed architecture and technical reference, see [.claude/CLAUDE.md](.claude/CLAUDE.md).
