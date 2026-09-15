from typing import Any

import anyio
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from treegen.config import Limits
from treegen.main import create_app
from treegen.security import TimeoutMiddleware

TREE_TEXT = "notebooks\n/config/ambiente"


def make_client(**overrides: Any) -> TestClient:
    return TestClient(create_app(limits=Limits(**overrides), env="development"))


def test_health():
    response = make_client().get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tree_ok():
    response = make_client().post("/api/tree", json={"text": TREE_TEXT})
    assert response.status_code == 200
    assert response.json() == {"result": "notebooks\n└── config\n    └── ambiente"}


def test_tree_modo_explicito():
    response = make_client().post(
        "/api/tree", json={"text": "raiz\n  a", "mode": "indentation"}
    )
    assert response.json() == {"result": "raiz\n└── a"}


def test_timeline_ok():
    response = make_client().post("/api/timeline", json={"text": "13/08 | Evento"})
    assert response.status_code == 200
    assert response.json() == {"result": "● 13/08 ───── Evento"}


def test_entrada_vazia_retorna_400():
    response = make_client().post("/api/tree", json={"text": "   "})
    assert response.status_code == 400


def test_timeline_sem_eventos_retorna_400():
    response = make_client().post("/api/timeline", json={"text": "nada aqui"})
    assert response.status_code == 400


def test_campo_extra_retorna_422():
    response = make_client().post("/api/tree", json={"text": "raiz", "x": 1})
    assert response.status_code == 422


def test_modo_invalido_retorna_422():
    response = make_client().post("/api/tree", json={"text": "raiz", "mode": "xyz"})
    assert response.status_code == 422


def test_texto_acima_do_limite_retorna_422():
    response = make_client().post("/api/tree", json={"text": "a" * 50_001})
    assert response.status_code == 422


def test_linhas_acima_do_limite_retorna_422():
    text = "\n".join(["raiz"] + [f"n{i}" for i in range(2_500)])
    response = make_client().post("/api/tree", json={"text": text})
    assert response.status_code == 422


def test_content_type_errado_retorna_415():
    response = make_client().post("/api/tree", data={"text": "raiz"})
    assert response.status_code == 415


def test_corpo_grande_retorna_413():
    response = make_client(max_body_bytes=100).post(
        "/api/tree",
        content=b'{"text": "' + b"a" * 200 + b'"}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413


def test_headers_de_seguranca():
    response = make_client().get("/api/health")
    headers = response.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert "default-src 'self'" in headers["content-security-policy"]
    assert headers["cache-control"] == "no-store"


def test_headers_presentes_em_resposta_de_erro():
    response = make_client(max_body_bytes=100).post(
        "/api/tree",
        content=b'{"text": "' + b"a" * 200 + b'"}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413
    assert response.headers["x-content-type-options"] == "nosniff"


def test_rate_limit_retorna_429_com_retry_after():
    client = make_client(rate_limit=2, rate_burst=0, rate_window_seconds=60)
    assert client.post("/api/tree", json={"text": "raiz"}).status_code == 200
    assert client.post("/api/tree", json={"text": "raiz"}).status_code == 200
    response = client.post("/api/tree", json={"text": "raiz"})
    assert response.status_code == 429
    assert response.headers.get("retry-after")


def test_health_isento_do_rate_limit():
    client = make_client(rate_limit=0, rate_burst=0)
    for _ in range(5):
        assert client.get("/api/health").status_code == 200


def test_docs_desabilitados_em_producao():
    client = TestClient(create_app(env="production"))
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_docs_disponiveis_em_desenvolvimento():
    assert make_client().get("/openapi.json").status_code == 200


def test_index_estatico_servido_na_raiz():
    response = make_client().get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_assets_estaticos_servidos():
    client = make_client()
    css = client.get("/css/style.css")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    script = client.get("/js/app.js")
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]


def test_index_referencia_os_assets():
    body = make_client().get("/").text
    assert "/css/style.css" in body
    assert "/js/app.js" in body


def test_timeout_retorna_503():
    async def slow(_request: Request) -> PlainTextResponse:
        await anyio.sleep(0.2)
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", slow)])
    app.add_middleware(TimeoutMiddleware, seconds=0.01)
    response = TestClient(app).get("/")
    assert response.status_code == 503
