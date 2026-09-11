# CodeTree

Aplicação web **stateless** que gera, a partir de texto simples, **estruturas
de pastas** (tree) e **linhas do tempo** (timeline) com caracteres
Unicode/ASCII — `├`, `└`, `│`, `─`, `○`, `●` — com **preview em tempo real**,
**copiar**, **baixar TXT** e **tema claro/escuro**.

- **Backend:** FastAPI + `uv` (Python 3.12)
- **Frontend:** HTML + CSS + JavaScript puro, servido pelo próprio FastAPI
- **Sem banco de dados:** processamento 100% em memória; nada do usuário é
  persistido, e nenhum conteúdo enviado é registrado em log

O plano completo de implementação está em
[`codetree-plano-implementacao.md`](codetree-plano-implementacao.md).

---

## Sumário

- [Funcionalidades](#funcionalidades)
- [Como usar](#como-usar)
- [API](#api)
- [Configuração](#configuração)
- [Execução local](#execução-local)
- [Testes e lint](#testes-e-lint)
- [Docker](#docker)
- [Segurança](#segurança)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Estado do projeto](#estado-do-projeto)
- [Licença](#licença)

---

## Funcionalidades

**Geração**

- Estrutura de pastas com três modos de entrada (`auto`, `caminhos` e
  `indentação`) e **detecção automática** de formato.
- Linha do tempo com eventos (data) e subitens (`-`), destacando o **último
  evento** com `●`.

**Interface**

- **Preview em tempo real** (com *debounce* de 150 ms).
- **Copiar** para a área de transferência (com *fallback* para contextos não
  seguros).
- **Baixar TXT** direto no navegador (sem endpoint no servidor).
- **Tema claro/escuro**, seguindo o sistema e com alternância persistida.
- Abas **Árvore** / **Linha do Tempo**, acessível por teclado e com
  `aria-live` no resultado.
- Layout responsivo, com ações por ícones e *tooltips*.

---

## Como usar

### Estrutura de pastas

A primeira linha é a raiz. Duas formas de informar a hierarquia:

**Caminhos** (prefixo `/`, intermediários criados automaticamente):

```text
notebooks
/config/ambiente
/bronze/notebook 1
/bronze/notebook 2
/silver/notebook 1
/gold/notebook 1
```

**Indentação** (qualquer largura de recuo; 1 espaço por nível é o mais simples):

```text
notebooks
 config
  ambiente
 bronze
  notebook 1
```

Ambas produzem a mesma saída (a ordem de inserção é preservada):

```text
notebooks
├── config
│   └── ambiente
├── bronze
│   ├── notebook 1
│   └── notebook 2
├── silver
│   └── notebook 1
└── gold
    └── notebook 1
```

> Regras: duplicados são mesclados; tabs equivalem a 4 espaços; linhas em
> branco são ignoradas. No modo **auto**, se houver alguma linha iniciando com
> `/`, usa-se *caminhos*; caso contrário, *indentação*.

### Linha do tempo

- Uma linha iniciada por uma **data** (`dd/mm` ou `dd/mm/aaaa`) é um evento;
  o separador `|` antes do título é opcional.
- Linhas iniciadas por `-` são **subitens** do evento anterior.
- O **último** evento recebe `●`; os demais, `○`.

```text
13/08 | Alteração da origem do atributo

02/09 | Adequação do ALTER TABLE
  - Truncate
  - Recarga da tabela

04/09 | Reinício da Identity
  - Truncate
  - Reset da Identity
```

```text
○ 13/08 ───── Alteração da origem do atributo
│
○ 02/09 ───── Adequação do ALTER TABLE
│             ├── Truncate
│             └── Recarga da tabela
│
● 04/09 ───── Reinício da Identity
              ├── Truncate
              └── Reset da Identity
```

---

## API

| Método | Rota            | Descrição                   |
|--------|-----------------|-----------------------------|
| `GET`  | `/api/health`   | Healthcheck                 |
| `POST` | `/api/tree`     | Gera a estrutura de pastas  |
| `POST` | `/api/timeline` | Gera a linha do tempo       |
| `GET`  | `/`             | Interface web (arquivos estáticos) |

### `POST /api/tree`

```jsonc
// requisição
{ "text": "projeto\n src\n  componentes", "mode": "auto" }

// resposta 200
{ "result": "projeto\n└── src\n    └── componentes" }
```

`mode`: `"auto"` (padrão) · `"paths"` · `"indentation"`.

### `POST /api/timeline`

```jsonc
// requisição
{ "text": "01/03 | Início\n  - Planejamento" }

// resposta 200
{ "result": "● 01/03 ───── Início\n              └── Planejamento" }
```

### Códigos de erro

Formato padrão: `{ "detail": "..." }`.

| Código | Quando |
|--------|--------|
| `400`  | Regra de conteúdo (ex.: entrada vazia, subitem sem evento) |
| `413`  | Corpo da requisição acima do limite |
| `415`  | `Content-Type` diferente de `application/json` |
| `422`  | Falha de validação ou limite de entrada excedido |
| `429`  | Excesso de requisições (com header `Retry-After`) |
| `503`  | Tempo de processamento excedido |
| `500`  | Erro interno (sem stack trace) |

### Limites

| Limite | Valor |
|--------|-------|
| Tamanho do campo `text` | 50.000 caracteres |
| Linhas por requisição | 2.000 |
| Nós na árvore / profundidade | 2.000 / 50 |
| Eventos / subitens por evento | 500 / 200 |
| Corpo da requisição | 64 KB |
| Timeout de processamento | 2 s |
| Rate limit por IP | ~120 req/min (+ burst de 20) |

### Exemplos com `curl`

```bash
curl -s -X POST http://127.0.0.1:8530/api/tree \
  -H 'Content-Type: application/json' \
  -d '{"text": "notebooks\n/config/ambiente", "mode": "auto"}'

curl -s -X POST http://127.0.0.1:8530/api/timeline \
  -H 'Content-Type: application/json' \
  -d '{"text": "13/08 | Evento A\n- item 1\n\n04/09 | Evento B"}'
```

---

## Configuração

Tudo é configurável por variáveis de ambiente `CODETREE_*` (ver
`src/codetree/config.py`):

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `CODETREE_HOST` | `127.0.0.1` | Endereço de escuta |
| `CODETREE_PORT` | `8530` | Porta |
| `CODETREE_ENV` | `development` | `production` desabilita `/docs`, `/redoc` e `/openapi.json` |
| `CODETREE_REQUEST_TIMEOUT` | `2` | Timeout de processamento (s) |
| `CODETREE_MAX_BODY_BYTES` | `65536` | Tamanho máximo do corpo |
| `CODETREE_RATE_LIMIT` | `120` | Requisições por janela, por IP |
| `CODETREE_RATE_BURST` | `20` | Burst adicional |
| `CODETREE_RATE_WINDOW` | `60` | Janela do rate limit (s) |
| `CODETREE_LIMIT_CONCURRENCY` | `32` | Concorrência máxima (uvicorn) |
| `CODETREE_TIMEOUT_KEEP_ALIVE` | `10` | Keep-alive (uvicorn) |
| `CODETREE_LIMIT_MAX_REQUESTS` | `10000` | Reciclagem de worker (uvicorn) |
| `CODETREE_FORWARDED_ALLOW_IPS` | `127.0.0.1` | Proxies confiáveis para `X-Forwarded-For` |

---

## Execução local

```bash
uv sync                  # cria o .venv e instala as dependências
uv run codetree          # http://127.0.0.1:8530
```

---

## Testes e lint

```bash
uv run pytest            # 58 testes
uv run ruff check .      # lint
```

A suíte cobre os geradores (testes *golden* com os exemplos canônicos),
a sanitização de entrada e os contratos/limites/headers da API.

---

## Docker

```bash
docker compose up --build      # http://localhost:8530
```

O `Dockerfile` é multi-stage (build com a imagem do `uv`, runtime enxuto) e o
`docker-compose.yml` aplica o endurecimento:

- roda como usuário **não-root** (`uid 1001`);
- `read_only: true` + `tmpfs` em `/tmp`;
- `cap_drop: [ALL]` e `security_opt: no-new-privileges:true`;
- limites de CPU (`1.0`) e memória (`256M`);
- `CODETREE_ENV=production` (docs desabilitadas);
- `HEALTHCHECK` em `/api/health` (fica `healthy`).

---

## Segurança

- **XSS:** o resultado é renderizado no frontend apenas com `textContent`.
- **CSP e headers** em todas as respostas (`Content-Security-Policy`,
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`, COOP/CORP), com `Cache-Control: no-store` na API e HSTS
  sob HTTPS.
- **Sem CORS:** frontend e API na mesma origem.
- **CSRF:** a API aceita somente `Content-Type: application/json` (`415` caso
  contrário).
- **Anti-DDoS:** rate limit por IP, timeout de processamento, limite de corpo
  à prova de *chunked*, limites de entrada e concorrência máxima.
- **Sanitização:** remoção de controles C0/C1 e de caracteres bidi/zero-width.
- **Sem persistência e sem log de conteúdo:** nenhum dado do usuário é gravado.
- **Docs desabilitadas em produção** e erro interno sem stack trace.

---

## Estrutura do projeto

```text
codetree/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── codetree-plano-implementacao.md
├── src/
│   └── codetree/
│       ├── __init__.py        # entrypoint (uvicorn)
│       ├── main.py            # app FastAPI (rotas, static, erros)
│       ├── config.py          # limites e ambiente
│       ├── schemas.py         # modelos Pydantic
│       ├── security.py        # middlewares de segurança
│       ├── sanitize.py        # limpeza de entrada
│       ├── errors.py          # InputError / LimitError
│       ├── services/
│       │   ├── tree.py        # build_tree (puro)
│       │   └── timeline.py    # build_timeline (puro)
│       └── static/            # frontend (HTML/CSS/JS)
└── tests/
    ├── test_tree.py
    ├── test_timeline.py
    ├── test_sanitize.py
    └── test_api.py
```

---

## Estado do projeto

Todas as fases planejadas (0 a 4) foram concluídas:

| Fase | Escopo | Situação |
|------|--------|----------|
| 0 | Fundação (uv, pacote, `/api/health`) | ✅ |
| 1 | Núcleo de geração (árvore e timeline) | ✅ |
| 2 | API, schemas, segurança e limites | ✅ |
| 3 | Frontend (preview, copiar, TXT, tema) | ✅ |
| 4 | Empacotamento (Docker e compose) | ✅ |
| 5 | Compartilhar por URL, templates, importar TXT, `/api/validate` | ⏳ |

**Notas**

- A imagem final usa `python:3.12-slim`, que ainda contém `/bin/sh`. Removê-lo
  exigiria uma base *distroless* (possível evolução na Fase 5); a postura de
  segurança hoje vem de `read_only` + `cap_drop: ALL` + `no-new-privileges` +
  não-root.
- Ao usar Docker, rode `docker compose up --build` após alterações no frontend,
  pois os arquivos estáticos são embutidos na imagem.

---

## Licença

Distribuído sob a licença **MIT**: qualquer pessoa pode usar, copiar, modificar
e distribuir este software, inclusive comercialmente, desde que mantidos o
aviso de copyright e esta licença. O software é fornecido "como está", sem
garantias. Veja [`LICENSE`](LICENSE).
