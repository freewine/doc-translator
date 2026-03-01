---
inclusion: always
---

# Technology Stack

## Backend

- Python 3.12+ with `uv` package manager
- Strawberry GraphQL (ASGI) + Starlette
- Uvicorn ASGI server
- boto3 for AWS Bedrock, DynamoDB, S3
- PyJWT + bcrypt for authentication
- Pillow for image handling
- python-dotenv for environment configuration

### Document Processing Libraries
- openpyxl - Excel (.xlsx) manipulation
- python-docx - Word (.docx) processing
- python-pptx - PowerPoint (.pptx) processing
- PyMuPDF (fitz) - PDF text extraction and reconstruction

### Testing
- pytest + pytest-asyncio (async test support, `asyncio_mode = "auto"`)
- hypothesis for property-based testing

## Frontend

- Vue 3 with Composition API + TypeScript
- Vite 7.x build tool
- Pinia state management
- Vue Router
- Apollo Client 4.x for GraphQL
- Ant Design Vue 4.x UI components
- vue-i18n for internationalization (zh, vi, en)

## Infrastructure

- AWS CDK (TypeScript) in `ecs/` directory
- ECS Fargate deployment with ALB
- Auto-scaling (1–4 tasks, 70% CPU target)

## AWS Services

- Amazon Bedrock (Converse API)
- Amazon DynamoDB (thesaurus, users, job history, config storage)
- Amazon S3 (document file storage - required)
- Amazon ECS Fargate (production deployment)
- Models: Nova Pro/Lite/2 Lite, Claude Sonnet/Haiku 4.5

## Common Commands

### Backend
```bash
cd backend
uv sync                          # Install dependencies
uv sync --extra dev              # Install with dev dependencies (pytest, hypothesis)
uv run main.py                   # Start server (localhost:8000)
uv run pytest tests/ -v          # Run tests
```

### Frontend
```bash
cd frontend
npm install                      # Install dependencies
npm run dev                      # Start dev server (localhost:5173)
npm run build                    # Production build
npm run preview                  # Preview production build
```

### Docker
```bash
docker compose up --build        # Build and run all services
```

### E2E Tests
```bash
cd e2e-tests
uv sync                          # Install dependencies
uv run python run_e2e_tests.py   # Run E2E tests
```

## Configuration

### Backend (`backend/.env`)
- `AWS_DEFAULT_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `JWT_SECRET` - JWT signing secret
- `S3_BUCKET` - S3 bucket for file storage (required)
- `MAX_CONCURRENT_FILES`, `TRANSLATION_BATCH_SIZE` - Concurrency settings
- `MAX_FILE_SIZE` - Upload size limit in bytes
- `LOG_LEVEL` - Logging level (default: INFO)
- `FRONTEND_URL` - For CORS (default: http://localhost:3000)

### Frontend (`frontend/.env`)
- `VITE_API_URL` - GraphQL endpoint (default: http://localhost:8000/api/graphql)
- `VITE_POLL_INTERVAL_MS` - Job polling interval
- `VITE_MAX_FILE_SIZE_MB` - Upload size limit

### Runtime Config
- Configuration stored in DynamoDB (global config, language pairs, user settings)
- Default admin user auto-created on first startup if no admins exist
