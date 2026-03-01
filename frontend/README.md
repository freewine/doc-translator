# Doc Translation Frontend

Vue 3 SPA for the Doc Translation System with TypeScript and Ant Design Vue.

## Quick Start

```bash
cd frontend
npm install                # Install dependencies
cp .env.example .env       # Configure environment
npm run dev                # Start dev server
```

Application runs on http://localhost:5173

## Architecture

```
frontend/src/
├── views/                 # Page components (Login, Main, Settings)
├── components/            # Reusable components
│   ├── FileUploader.vue          # Drag-and-drop file upload
│   ├── LanguagePairSelector.vue  # Language pair dropdown
│   ├── ProgressTracker.vue       # Real-time progress display
│   ├── NavigationMenu.vue        # App navigation
│   └── ErrorDisplay.vue          # Error handling UI
├── stores/                # Pinia state management
│   ├── auth.ts            # Authentication state
│   ├── job.ts             # Translation job state
│   └── config.ts          # Configuration state
├── services/              # API integration
│   ├── apollo.ts          # Apollo Client setup
│   └── api.ts             # REST API wrapper
├── graphql/               # GraphQL queries/mutations
├── composables/           # Vue composition functions
├── i18n/                  # Internationalization (zh/vi)
├── router/                # Vue Router configuration
└── types/                 # TypeScript definitions
```

## Configuration

### Environment Variables (.env)

See `.env.example` for a complete template with comments.

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000/api/graphql` | Backend GraphQL API endpoint |

## Routes

| Route | Description | Auth Required |
|-------|-------------|---------------|
| `/login` | User authentication | No |
| `/main` | Translation interface | Yes |
| `/settings` | Language pair management | Yes |

## Commands

```bash
npm run dev        # Development server with hot reload
npm run build      # Production build
npm run preview    # Preview production build
```

## Key Features

- **JWT Authentication** with localStorage persistence
- **File Upload** with drag-and-drop and validation (.xlsx, .docx, .pptx, .pdf)
- **Real-time Progress** with configurable polling interval
- **Language Pair Management** via settings page
- **Responsive Design** (mobile, tablet, desktop)
- **Internationalization** (Chinese/Vietnamese UI)
- **Error Handling** with retry functionality

## State Management

- **Auth Store**: Login/logout, token management, session persistence
- **Job Store**: Current job, job history, progress tracking
- **Config Store**: Language pairs, app settings

## GraphQL Integration

Apollo Client configured with:
- Authentication link (JWT token attachment)
- Error handling link (auto-logout on auth errors)
- In-memory cache with type policies

---

[Back to main README](../README.md)
