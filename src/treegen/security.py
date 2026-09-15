"""Middlewares de segurança: headers, limites de entrada e disponibilidade.

Ordem de montagem (do externo para o interno):

``SecurityHeaders`` → ``RateLimit`` → ``ContentTypeGuard`` → ``BodySizeLimit``
→ ``Timeout`` → rotas.

Assim os headers são aplicados a **toda** resposta (inclusive 413/415/429/503),
requisições abusivas são barradas cedo e o corpo só é lido se o
``Content-Type`` for aceitável.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import cast, override

from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_BODY_METHODS = frozenset(["POST", "PUT", "PATCH"])

_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona headers de segurança e evita cache de respostas da API."""

    def __init__(self, app: ASGIApp, cache_no_store_prefix: str = "/api/") -> None:
        super().__init__(app)
        self.cache_prefix: str = cache_no_store_prefix

    @override
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for name, value in _SECURITY_HEADERS.items():
            if name not in response.headers:
                response.headers[name] = value
        if request.url.path.startswith(self.cache_prefix) and "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store"
        if request.url.scheme == "https" and "Strict-Transport-Security" not in response.headers:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Interrompe o processamento que exceder o tempo limite (§6.5)."""

    def __init__(self, app: ASGIApp, seconds: float) -> None:
        super().__init__(app)
        self.seconds: float = seconds

    @override
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            async with asyncio.timeout(self.seconds):
                return await call_next(request)
        except TimeoutError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Tempo de processamento excedido."},
            )


class ContentTypeGuardMiddleware(BaseHTTPMiddleware):
    """Recusa requisições com corpo que não sejam JSON (anti-CSRF)."""

    def __init__(
        self,
        app: ASGIApp,
        prefixes: tuple[str, ...] = ("/api/",),
        methods: frozenset[str] = _BODY_METHODS,
    ) -> None:
        super().__init__(app)
        self.prefixes: tuple[str, ...] = prefixes
        self.methods: frozenset[str] = methods

    @override
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in self.methods and request.url.path.startswith(self.prefixes):
            content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type != "application/json":
                return JSONResponse(
                    status_code=415,
                    content={"detail": "Content-Type deve ser application/json."},
                )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limite de requisições por IP com janela deslizante em memória.

    O estado é por processo; múltiplas réplicas exigiriam um limitador
    compartilhado (documentado no plano, §6.5).
    """

    def __init__(
        self,
        app: ASGIApp,
        limit: int,
        burst: int,
        window: float,
        exempt_paths: tuple[str, ...] = (),
        max_keys: int = 10_000,
    ) -> None:
        super().__init__(app)
        self.max_requests: int = max(0, limit) + max(0, burst)
        self.window: float = max(0.001, window)
        self.exempt: frozenset[str] = frozenset(exempt_paths)
        self.max_keys: int = max_keys
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    @override
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self.exempt:
            return await call_next(request)

        client = request.client
        ip = client.host if client is not None else "desconhecido"
        now = time.monotonic()
        hits = self._hits[ip]
        while hits and now - hits[0] >= self.window:
            del hits[0]

        if len(hits) >= self.max_requests:
            seconds = int(self.window - (now - hits[0])) + 1 if hits else int(self.window) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Muitas requisições. Tente novamente em instantes."},
                headers={"Retry-After": str(max(1, seconds))},
            )

        hits.append(now)
        if len(self._hits) > self.max_keys:
            self._prune()
        return await call_next(request)

    def _prune(self) -> None:
        for key in [key for key, hits in self._hits.items() if not hits]:
            del self._hits[key]


class BodySizeLimitMiddleware:
    """Limita o tamanho do corpo, inclusive sem ``Content-Length`` (chunked).

    Bufferiza no máximo ``max_bytes`` antes de repassar à aplicação, evitando
    consumo ilimitado de memória.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app: ASGIApp = app
        self.max_bytes: int = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _BODY_METHODS:
            await self.app(scope, receive, send)
            return

        length = Headers(scope=scope).get("content-length")
        if length is not None and length.isdigit() and int(length) > self.max_bytes:
            await self._reject(scope, receive, send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body.extend(cast(bytes, message.get("body", b"")))
            if len(body) > self.max_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        buffered = bytes(body)
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if replayed:
                return {"type": "http.disconnect"}
            replayed = True
            return {"type": "http.request", "body": buffered, "more_body": False}

        await self.app(scope, replay, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=413,
            content={"detail": "Corpo da requisição muito grande."},
        )
        await response(scope, receive, send)
