---
inclusion: always
---

# Backend Development

## Package Management
- Use `uv` for Python package management
- Install dependencies: `uv sync` (production) or `uv sync --extra dev` (development)

## Running Commands
- Start server: `uv run main.py` (from `backend/` directory)
- Run any Python file: `uv run <filename.py>`
- Run tests: `uv run pytest tests/ -v`

# Frontend Development

## Package Management
- Use `npm` for Node.js package management
- Install dependencies: `npm install` (from `frontend/` directory)

## Running Commands
- Start dev server: `npm run dev`
- Build for production: `npm run build`
