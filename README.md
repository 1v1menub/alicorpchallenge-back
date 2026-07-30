# Alicorp · Fábrica Creativa — Backend

FastAPI backend for the Alicorp "Content Suite" IAGen challenge: an AI platform for
generating brand-consistent content. It generates structured **brand manuals** from a
brief (stored with pgvector for RAG), produces **ads** grounded in the relevant manual
sections, runs an advisory **multimodal image audit** plus human approval flows, and
traces every AI call to **Langfuse**.

**Live app:** https://alicorpchallenge-front.vercel.app

**API:** https://alicorpchallenge-back.onrender.com · [docs](https://alicorpchallenge-back.onrender.com/docs)

**Frontend repo:** https://github.com/1v1menub/alicorpchallenge-front · **Presentación:** [slides.pdf](slides.pdf)

## Stack

- **FastAPI** + **uv** (Python 3.13)
- **SQLAlchemy 2.0 (async)** + **asyncpg** + **pgvector**
- **Groq** `llama-3.3-70b-versatile` (text) · **Gemini** `gemini-embedding-001` (embeddings, 768-d) · `gemini-flash-latest` (vision)
- **PyJWT** (HS256) auth with role → module RBAC
- **Supabase** Postgres + Storage
- **Langfuse** observability — [traces dashboard](https://us.cloud.langfuse.com/project/cms7945ib00vwad0dkcku4uhg/traces) (requires login)

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Python 3.13
- A Postgres database **with the `pgvector` extension** — either the bundled Docker
  container (below) or a Supabase project.

## Setup

```bash
uv sync
cp .env.example .env      # then fill in the values (see below)
```

### Environment (`.env`)

| Var | What |
| --- | --- |
| `DATABASE_URL` | Async Postgres URL (`postgresql+asyncpg://…`) |
| `JWT_SECRET` / `JWT_ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` | Auth |
| `SEED_PASSWORD` | Password given to every seeded user (default `password123`) |
| `CORS_ORIGINS` | JSON array of allowed origins, e.g. `["http://localhost:5173"]` |
| `GROQ_API_KEY` | Groq (text generation) |
| `GOOGLE_API_KEY` | Gemini (embeddings + vision) |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL` | Tracing (optional — omit to disable) |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` / `SUPABASE_STORAGE_BUCKET` | Storage for audited images (needed for the image-audit flow) |

## Database

Pick one:

**A) Local Docker (pgvector included):**

```bash
docker compose up -d
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/content_suite
```

**B) Supabase:** enable the `vector` extension (Database → Extensions), and use the
**Session pooler** connection string (port **5432**, *not* the 6543 transaction pooler,
*not* the IPv6-only direct connection), with the scheme changed to `postgresql+asyncpg://`:

```
DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

## Run

```bash
uv run uvicorn main:app --reload
```

- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

On startup the app enables `pgvector`, creates all tables, and **seeds** the roles,
modules, and one user per role (idempotent).

## Seeded users

All use the password from `SEED_PASSWORD` (default `password123`):

| Username | Role | Access |
| --- | --- | --- |
| `creador` | Creador | Create manuals & ads |
| `aprobador_a` | Aprobador A | Audit/approve text ads |
| `aprobador_b` | Aprobador B | Audit/approve image ads |
| `admin` | Administrador | Everything |

Everyone can view manuals and ads; creation and approval are gated by role.

## Docker

```bash
docker build -t content-suite-api .
docker run --env-file .env -p 8000:8000 content-suite-api
```

The image binds `0.0.0.0:${PORT:-8000}`, so it runs as-is on hosts like Render.
