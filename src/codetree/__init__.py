"""CodeTree — gerador de estruturas Unicode/ASCII (tree e timeline)."""

from __future__ import annotations

import os


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def main() -> None:
    """Sobe o servidor HTTP via uvicorn.

    Host e porta podem ser sobrescritos por ``CODETREE_HOST`` e
    ``CODETREE_PORT`` (no container o host precisa ser ``0.0.0.0``).
    """
    import uvicorn

    host = os.environ.get("CODETREE_HOST", "127.0.0.1")
    port = _env_int("CODETREE_PORT", 8530)
    uvicorn.run(
        "codetree.main:app",
        host=host,
        port=port,
        limit_concurrency=_env_int("CODETREE_LIMIT_CONCURRENCY", 32),
        timeout_keep_alive=_env_int("CODETREE_TIMEOUT_KEEP_ALIVE", 10),
        limit_max_requests=_env_int("CODETREE_LIMIT_MAX_REQUESTS", 10_000),
        forwarded_allow_ips=os.environ.get("CODETREE_FORWARDED_ALLOW_IPS", "127.0.0.1"),
    )


if __name__ == "__main__":
    main()
