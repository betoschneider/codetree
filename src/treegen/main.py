"""Aplicação FastAPI do TreeGen."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp

from .config import Limits, configured_root_path, current_environment, load_limits
from .errors import InputError, LimitError
from .schemas import ResultResponse, TimelineRequest, TreeRequest
from .security import (
    BodySizeLimitMiddleware,
    ContentTypeGuardMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    TimeoutMiddleware,
)
from .services.timeline import build_timeline
from .services.tree import build_tree

logger = logging.getLogger("treegen")

STATIC_DIR = Path(__file__).parent / "static"


def _generate(operation: Callable[[], str]) -> ResultResponse:
    """Executa um gerador, traduzindo erros de domínio em HTTP."""
    try:
        return ResultResponse(result=operation())
    except InputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LimitError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def create_app(limits: Limits | None = None, env: str | None = None) -> FastAPI:
    """Cria a aplicação. ``env="production"`` desabilita as docs."""
    limits = limits or load_limits()
    is_production = (env or current_environment()) == "production"

    if is_production:
        app = FastAPI(
            title="TreeGen",
            version="0.1.0",
            docs_url=None,
            redoc_url=None,
            openapi_url=None,
        )
    else:
        app = FastAPI(title="TreeGen", version="0.1.0")

    # Ordem: o primeiro `add_middleware` fica mais interno.
    app.add_middleware(TimeoutMiddleware, seconds=limits.request_timeout_seconds)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=limits.max_body_bytes)
    app.add_middleware(ContentTypeGuardMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        limit=limits.rate_limit,
        burst=limits.rate_burst,
        window=limits.rate_window_seconds,
        exempt_paths=("/api/health",),
    )
    app.add_middleware(SecurityHeadersMiddleware, cache_no_store_prefix="/api/")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        """Healthcheck usado pelo Docker e por monitoramento."""
        return {"status": "ok"}

    @app.post("/api/tree", response_model=ResultResponse)
    async def generate_tree(payload: TreeRequest) -> ResultResponse:
        return _generate(lambda: build_tree(payload.text, payload.mode.value))

    @app.post("/api/timeline", response_model=ResultResponse)
    async def generate_timeline(payload: TimelineRequest) -> ResultResponse:
        return _generate(lambda: build_timeline(payload.text))

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        # Loga o tipo/traceback, nunca o conteúdo enviado pelo usuário.
        logger.exception("Erro interno ao processar a requisição", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Erro interno."})

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


def create_asgi_app(
    limits: Limits | None = None,
    env: str | None = None,
    root_path: str | None = None,
) -> ASGIApp:
    """Cria a aplicação, opcionalmente acessível também sob um prefixo.

    Serve para quando o proxy encaminha o caminho completo (ex.: Cloudflare
    entregando ``/treegen/...``). A raiz continua funcionando, então a mesma
    imagem atende subdomínio e subcaminho.
    """
    app = create_app(limits=limits, env=env)
    prefix = (configured_root_path() if root_path is None else root_path).strip("/")
    if not prefix:
        return app

    outer = FastAPI(
        title="TreeGen",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @outer.get(f"/{prefix}")
    async def _redirect_to_prefix() -> RedirectResponse:
        """Leva ``/prefixo`` para ``/prefixo/`` (senão os caminhos relativos quebram)."""
        return RedirectResponse(url=f"/{prefix}/", status_code=307)

    # O prefixo vem antes para casar exatamente; "/" é o fallback.
    outer.mount(f"/{prefix}", app)
    outer.mount("/", app)
    outer.add_middleware(SecurityHeadersMiddleware, cache_no_store_prefix="/api/")
    return outer


app = create_asgi_app()
