# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Doc Translation System - a web application that translates documents (Excel, Word, PowerPoint, PDF, Text, Markdown) between languages using Amazon Bedrock LLM models while preserving formatting.

## Commands

### Backend (Python 3.12+ / uv)
```bash
cd backend
uv sync                          # Install dependencies
uv sync --extra dev              # Install with dev dependencies
uv run main.py                   # Start server (http://localhost:8000)
uv run pytest tests/ -v          # Run all tests
uv run pytest tests/test_foo.py -v  # Run single test file
uv run pytest -k "test_name"     # Filter specific tests
uv run pytest -q --tb=short      # Minimal output (preferred)
uv run python -m src.cli.commands create-admin  # CLI user management
uv run python -m src.cli.commands create-tables # Create DynamoDB tables
```

### Frontend (Vue 3 / npm)
```bash
cd frontend
npm install                      # Install dependencies
npm run dev                      # Dev server (http://localhost:5173)
npm run build                    # Type-check (vue-tsc) + production build
```

### E2E Tests
```bash
cd e2e-tests
uv sync
uv run python run_e2e_tests.py --mode full    # Full suite
uv run python run_e2e_tests.py --mode api     # API-only
uv run pytest test_e2e_chrome_devtools.py -v -m "api"  # Specific tests
```

### Docker
```bash
docker compose up --build -d     # Frontend: localhost:3000, Backend: localhost:8000
```

### ECS CDK Deployment
```bash
cd ecs
npm install
npx cdk bootstrap               # First-time only (per AWS account/region)
npx cdk deploy                  # Deploy (requires S3_BUCKET, JWT_SECRET env vars)
npx cdk destroy                 # Tear down all resources
```

## First-Time Setup

On first run, the backend auto-creates a default admin user if none exists. A random temporary password is generated and logged to the console once (check logs for `Default admin created with temporary password: <random>`). Change this immediately. Alternatively, use the CLI: `uv run python -m src.cli.commands create-admin --username admin --password <pass>`.

## Architecture

### Backend (`backend/src/`)
- **GraphQL API**: Strawberry GraphQL + Starlette + Uvicorn
- **Entry point**: `main.py` - ASGI app with lifespan management, auto-initializes DynamoDB tables on startup
- **Config**: `.env` file (required: `JWT_SECRET`, `S3_BUCKET`); runtime config stored in DynamoDB
- **Structure**:
  - `graphql/` - Schema definitions (`schema.py`) and resolvers
  - `services/` - Business logic (translation, document processing, auth, thesaurus, config)
  - `models/` - Data models (`job.py`, `user.py`, `config.py`, `thesaurus.py`)
  - `storage/` - S3 file storage, job persistence (dual: in-memory `JobStore` + DynamoDB `JobRepository`)
  - `core/` - `app_config.py` (environment-based configuration)
  - `cli/` - CLI commands for user management

### Frontend (`frontend/src/`)
- **Framework**: Vue 3 + TypeScript + Ant Design Vue + Apollo Client
- **Path alias**: `@` maps to `./src` (configured in `vite.config.ts`)
- **Proxy**: Dev server proxies `/api` requests to `http://localhost:8000`
- **Build arg**: `VITE_API_URL` (default: `/api/graphql`) for Docker/ECS deployments
- **Key directories**: `views/`, `components/`, `stores/` (Pinia), `graphql/`, `composables/`, `i18n/locales/` (zh.json, vi.json)

### Translation Pipeline

1. File uploaded to S3 at `{user_id}/uploads/{file_id}/{filename}`
2. Job created with file IDs, language pair, and optional thesaurus catalogs
3. `TranslationOrchestrator` coordinates processing:
   - `DocumentProcessorFactory` selects processor by file extension
   - `extract_text()` pulls translatable `TextSegment`s with metadata
   - `TranslationService.batch_translate_async()` calls Bedrock with batched segments
   - `write_translated()` writes translations back preserving formatting
4. Output uploaded to S3 at `{user_id}/jobs/{job_id}/{filename}`
5. Job status updated throughout via callbacks to `TranslationJob` model

### Key Patterns

**Document Processor Pattern**: Abstract `DocumentProcessor` base class with format-specific implementations (Excel, Word, PowerPoint, PDF, Text, Markdown). Factory pattern selects processor. All implement:
- `supported_extensions` / `extract_text()` / `write_translated()` / `validate_file()`

**Output Modes** (mutually exclusive, configured per job):
- **Replace** (default): Translated text replaces original
- **Append** (`auto_append=True`): Translation appended after original text
- **Interleaved** (`interleaved_mode=True`): Original and translated lines alternated

**Dual Job Storage**: Active jobs in `JobStore` (in-memory) for fast access; persisted to `JobRepository` (DynamoDB) after each status change.

**Service Injection**: Services injected via `ResolverContext` in GraphQL resolvers.

**Bedrock Retry**: Exponential backoff (3 attempts, 1s/2s/4s delays) for `ThrottlingException`, `ValidationException`, `ServiceUnavailableException`. Falls back to original text on final failure.

**Thesaurus**: Terms organized by language pair → catalog → term pairs. Injected into translation system prompt via `get_terms_for_translation()` → `_build_system_prompt()`.

**Frontend**: Composition API with `<script setup>`, Pinia stores with localStorage persistence, Apollo Client with polling for job updates.

### Test Configuration

- pytest with `asyncio_mode = "auto"` (no need for `@pytest.mark.asyncio` on async tests)
- `asyncio_default_fixture_loop_scope = "function"`
- Dev dependencies: pytest, pytest-asyncio, hypothesis, httpx

## Supported Document Formats

| Format | Library | Capabilities |
|--------|---------|--------------|
| Excel (.xlsx) | openpyxl | Cells, formatting, images, charts |
| Word (.docx) | python-docx | Paragraphs, tables, headers/footers, text boxes |
| PowerPoint (.pptx) | python-pptx | Slides, shapes, notes, animations |
| PDF (.pdf) | PyMuPDF (fitz) | Text blocks, layout preservation (text-based only) |
| Text (.txt) | Built-in | Paragraph-based splitting (double-newline delimited) |
| Markdown (.md) | Built-in | Line-level parsing, preserves code blocks and front matter |

## Supported AI Models

| Model | ID |
|-------|-----|
| Nova 2 Lite (default) | `global.amazon.nova-2-lite-v1:0` |
| Claude Sonnet 4.5 | `global.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Claude Haiku 4.5 | `global.anthropic.claude-haiku-4-5-20251001-v1:0` |

## AWS Services

- **Amazon Bedrock** (Converse API) - Translation via LLM models
- **Amazon DynamoDB** - 7 tables prefixed `doc_translation_` (jobs, users, term_pairs, catalogs, language_pairs, user_settings, global_config)
- **Amazon S3** - File storage (uploads, translated outputs) with presigned URLs for downloads

## Environment Variables

Required in `backend/.env`:
- `JWT_SECRET` - JWT signing key
- `S3_BUCKET` - S3 bucket for file storage

Optional:
- `MAX_CONCURRENT_FILES` (default: 5)
- `TRANSLATION_BATCH_SIZE` (default: 10)
- `MAX_FILE_SIZE` (default: 52428800 / 50MB)
- `FRONTEND_URL` - For CORS (default: `http://localhost:3000`)
- `HOST` / `PORT` (default: `0.0.0.0` / `8000`)
- `DEBUG` / `RELOAD` (default: false) - Starlette debug and auto-reload
- `LOG_LEVEL` (default: INFO) - Logs to console + `backend/logs/backend.log`

## API Endpoints (all under /api prefix)

- **GraphQL**: `/api/graphql` (GraphiQL playground available when `DEBUG=true`)
- **REST**: `POST /api/upload`, `GET /api/download?job_id=&filename=`, `GET /api/health`

## Coding Standards

- PEP 8, 88-char line limit (Black formatter style)
- Type hints required for function parameters and return values
- Use specific exception types and context managers for resource management
- See `.kiro/steering/python-best-practices.md` for full guidelines

## Deployment Options

- `docker-compose.yml` - Local Docker (`docker compose up --build -d`)
- `ecs/` - AWS ECS Fargate via CDK (`npx cdk deploy`); see `ecs/README.md` for architecture details
