---
inclusion: always
---

# Project Structure

```
.
├── backend/                    # Python GraphQL API
│   ├── main.py                # ASGI app entry point (Starlette + Strawberry)
│   ├── pyproject.toml         # Python dependencies (uv)
│   ├── src/
│   │   ├── core/
│   │   │   └── app_config.py        # AppConfig from environment variables
│   │   ├── models/
│   │   │   ├── job.py               # Job data models (JobStatus, TranslationJob)
│   │   │   ├── thesaurus.py         # Thesaurus models (TermPair, Catalog)
│   │   │   ├── user.py              # User model (User, UserRole, UserStatus)
│   │   │   └── config.py            # Configuration models
│   │   ├── services/
│   │   │   ├── auth_service.py           # JWT authentication
│   │   │   ├── user_service.py           # User CRUD and password management
│   │   │   ├── user_settings_service.py  # Per-user settings management
│   │   │   ├── document_processor.py     # Abstract base class for all processors
│   │   │   ├── excel_processor.py        # Excel read/write with openpyxl
│   │   │   ├── excel_document_processor.py # Excel DocumentProcessor implementation
│   │   │   ├── word_processor.py         # Word processing with python-docx
│   │   │   ├── powerpoint_processor.py   # PowerPoint processing with python-pptx
│   │   │   ├── pdf_processor.py          # PDF processing with PyMuPDF
│   │   │   ├── text_processor.py         # Plain text (.txt) processing
│   │   │   ├── markdown_processor.py     # Markdown (.md) processing
│   │   │   ├── translation_service.py    # Bedrock API integration
│   │   │   ├── translation_orchestrator.py # Job coordination
│   │   │   ├── job_manager.py            # Job lifecycle management
│   │   │   ├── concurrent_executor.py    # Parallel processing
│   │   │   ├── language_pair_service.py  # Language pair configuration
│   │   │   ├── global_config_service.py  # Global app configuration
│   │   │   └── thesaurus_service.py      # Term/catalog management
│   │   ├── storage/
│   │   │   ├── s3_file_storage.py   # S3 file storage (required)
│   │   │   ├── job_store.py         # In-memory job storage
│   │   │   ├── job_repository.py    # DynamoDB job persistence
│   │   │   └── dynamodb_repository.py # DynamoDB persistence for thesaurus/users/config
│   │   └── graphql/
│   │       ├── schema.py            # GraphQL type definitions
│   │       ├── resolvers.py         # Query/mutation implementations
│   │       ├── thesaurus_resolvers.py # Thesaurus GraphQL resolvers
│   │       ├── user_resolvers.py    # User management resolvers
│   │       ├── config_resolvers.py  # Configuration resolvers
│   │       └── decorators.py        # Auth/permission decorators
│   └── tests/                 # pytest + hypothesis test suite
│
├── frontend/                  # Vue 3 SPA
│   ├── src/
│   │   ├── main.ts           # App bootstrap
│   │   ├── App.vue           # Root component
│   │   ├── views/            # Page components (Login, Main, Settings, Thesaurus, UserManagement)
│   │   ├── components/       # Reusable UI components
│   │   ├── stores/           # Pinia stores (auth, job, config, thesaurus, user)
│   │   ├── composables/      # Vue composition functions
│   │   ├── services/         # API integration (apollo.ts, api.ts)
│   │   ├── graphql/          # Queries and mutations
│   │   ├── i18n/             # Internationalization (zh, vi, en)
│   │   └── types/            # TypeScript type definitions
│   └── vite.config.ts        # Vite configuration
│
├── ecs/                       # AWS CDK (TypeScript) - ECS Fargate deployment
│   ├── lib/doc-translation-stack.ts  # CDK stack (VPC, ECS, ALB, IAM, auto-scaling)
│   └── cdk.json
│
├── e2e-tests/                 # E2E test suite (Python + Chrome DevTools)
├── doc/                       # Sample input/output files
└── docker-compose.yml         # Multi-container orchestration
```

## Key Patterns

### Backend
- Services are injected via `ResolverContext` in GraphQL resolvers
- `AppContext` in main.py initializes all services at startup
- Async/await throughout with sync wrappers for backward compatibility
- Exponential backoff retry for Bedrock API calls
- Job progress tracked via callbacks to `TranslationJob` model
- **Document Processor Pattern**: Abstract `DocumentProcessor` base class with format-specific implementations
- Factory pattern for selecting appropriate processor based on file extension
- DynamoDB tables auto-created on startup via `initialize_tables()`

### Frontend
- Composition API with `<script setup>` syntax
- Pinia stores with localStorage persistence
- Apollo Client for GraphQL with polling for job updates
- Composables for reusable logic (useGraphQL, useFileDownload, useErrorHandler)

### API Endpoints (all under /api prefix)
- `POST /api/upload` - File upload (multipart/form-data, auth required)
- `GET /api/download?job_id=&filename=` - File download (auth required)
- `/api/graphql` - GraphQL API (queries, mutations)
- `/api/health` - Health check

### Document Processor Interface
All document processors implement:
- `supported_extensions` - List of handled file extensions
- `extract_text()` - Extract translatable text segments with metadata
- `write_translated()` - Write translations back preserving formatting
- `validate_file()` - Check file can be processed

### Storage Architecture
- `S3FileStorage` - S3 storage for file uploads and downloads (required)
- `JobStore` - In-memory job state during processing
- `JobRepository` - DynamoDB persistence for job history
- `DynamoDBRepository` - DynamoDB persistence for thesaurus, users, and config
