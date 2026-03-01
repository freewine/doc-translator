---
inclusion: always
---

# Product Overview

Doc Translation System — a web application that translates documents between languages using Amazon Bedrock LLM models.

## Core Functionality

- Upload documents via web UI (.xlsx, .docx, .pptx, .pdf, .txt, .md)
- Translate between languages via AWS Bedrock Converse API
- Preserve all document formatting (fonts, colors, styles, layout) and embedded content
- Download translated files with `_vi` suffix
- Manage term translation thesaurus for consistent terminology

## Supported Document Formats

| Format | Library | Capabilities |
|--------|---------|--------------|
| Excel (.xlsx) | openpyxl | Cells, formatting, images, charts |
| Word (.docx) | python-docx | Paragraphs, tables, headers/footers, text boxes |
| PowerPoint (.pptx) | python-pptx | Slides, shapes, notes, animations |
| PDF (.pdf) | PyMuPDF (fitz) | Text blocks, layout preservation (text-based only) |
| Text (.txt) | Built-in | Paragraph-based splitting (double-newline delimited) |
| Markdown (.md) | Built-in | Line-level parsing, preserves code blocks and front matter |

## Key Features

- Job-based translation with real-time progress tracking (polling)
- JWT authentication with role-based access control (admin/user)
- User management (admin can create users, reset passwords)
- Concurrent batch processing with configurable workers
- Multiple LLM model support (Nova Pro/Lite/2 Lite, Claude Sonnet/Haiku 4.5)
- Exponential backoff retry logic (3 attempts)
- Unified document processor interface for extensibility
- Internationalized UI (Chinese/Vietnamese/English)
- Term Translation Thesaurus with catalog organization and CSV import/export
- S3 storage for files (required), DynamoDB for job history and config

## Thesaurus Feature

- Organize term pairs by language pair and catalog (domain/project)
- CRUD operations for term pairs with validation
- CSV import/export for bulk term management
- Terms injected into translation system prompt for consistency
- Paginated search with filtering by catalog and source term

## User Flow

1. Login with JWT credentials (default admin: admin / admin@123)
2. (Optional) Manage thesaurus terms in catalogs
3. Upload documents (Excel, Word, PowerPoint, PDF, Text, or Markdown)
4. Select language pair and optional thesaurus catalogs
5. Start translation job
6. Monitor progress via polling
7. Download translated files
