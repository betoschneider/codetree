# syntax=docker/dockerfile:1

# ---- Estágio 1: dependências e build -------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependências primeiro, para aproveitar o cache de camadas.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project

# Código da aplicação.
COPY src ./src
RUN uv sync --frozen --no-dev

# ---- Estágio 2: runtime ---------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    CODETREE_HOST=0.0.0.0 \
    CODETREE_PORT=8530 \
    CODETREE_ENV=production

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Usuário sem privilégios (nunca rodar como root).
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --no-create-home --shell /usr/sbin/nologin app

USER app

EXPOSE 8530

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8530/api/health').read()"]

CMD ["codetree"]
