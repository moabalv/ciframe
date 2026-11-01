# Pesquisa: bancos embarcados viáveis (sem serviço externo adicional)

## Resumo
O projeto hoje **não tem banco de dados**: `main.py` lê `data/top/dataset_final.csv` uma vez no import e mantém tudo em memória (`musicas_dict`, `musicas`, `generos`, `acordes`). O deploy é intencionalmente local-only via Docker único (`Dockerfile`), sem alvo cloud definido (ADR-0001). Qualquer persistência nova para "sequências customizadas" precisa caber nesse modelo sem introduzir serviços externos. Hoje **não há volume configurado** na imagem/uso documentado.

## Estado atual relevante

### Deploy / container
- **ADR-0001** (`docs/adr/0001-local-only-docker-deploy.md:1-24`): substituiu App Engine/Heroku por `Dockerfile` único rodando localmente com gunicorn. Backend mantido (CSV em memória). Cloud deixado em aberto.
- **Dockerfile** (`Dockerfile:1-12`): `FROM python:3.9-slim`, `WORKDIR /app`, copia `requirements.txt` e instala com `--no-cache-dir`, copia `.`, expõe `8080`, `CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]`. Sem `VOLUME`, sem serviço de DB.
- **requirements.txt** (`requirements.txt:1-6`): apenas `Flask==3.1.3`, `gunicorn==23.0.0`.
- **AGENTS.md:1-60**: "loads `data/top/dataset_final.csv` into memory once at startup — there is no database." Gotcha: editar CSV requer restart.

### Código / arquitetura
- **Inicialização** (`main.py:1-100`): abre `data/top/dataset_final.csv` no import, parse linha a linha, constrói `musicas_dict`, `musicas`, `generos` (set), `acordes` (set). Tudo em memória.
- **Endpoints** (`main.py:170-223`): `/similares` faz matching por `acordes`/`id_unico_musica` (conjuntos) ou por **sequência famosa hardcoded** via lookup em `sequencias` (`main.py:40-45`) + `get_similares_por_sequencia` que filtra por `str(id_seq) in musica.seqs_famosas` (pré-computado no CSV). Não há endpoints para CRUD de sequências customizadas hoje.
- **Frontend** (`static/templates/sequencia.html`, `static/assets/js/controllers/sequencia.js:1-200`): tela `#/porsequencia` mostra **4 sequências hardcoded no JS** (`sequencia1`-`sequencia4`) e chama `GET /similares?sequencia=...` com string concatenada por vírgulas. Difere das 6 hardcoded no backend.

## Bancos embarcados viáveis (sem serviço externo adicional)

Considerando rodar dentro do mesmo container/processo, com Python stdlib ou dependências puramente locais.

| Opção | Tipo | Dependências | Persistência entre reinícios do container | Implicações p/ Dockerfile atual | Observações |
|---|---|---|---|---|---|
| **SQLite (`sqlite3` stdlib)** | Arquivo único `.db` | Nenhuma (stdlib) | **Depende de volume**. Se arquivo ficar em `/app/...` e o container for removido/recriado sem volume, perde dados. Se só reiniciar (`stop/start`) do mesmo container, persiste enquanto o container existir. Para persistir entre recriações, precisa bind mount/named volume (ex. `-v ./data:/data`). | Sem mudanças obrigatórias. Opcional: `RUN mkdir -p /data` e definir caminho. Sem adicionar pacotes em `requirements.txt`. | Mais adequado. SQL, transações, ACID, schema explícito, integração simples com Flask/gunicorn. Cabe em `python:3.9-slim`. |
| **JSON (`json` stdlib)** | Arquivo texto `.json` | Nenhuma (stdlib) | Mesma questão de arquivo/volume. | Sem deps. Sem alterações no `requirements.txt`. | Simples, legível. Sem ACID, sem concorrência/transações nativas. Com gunicorn multi-worker, acesso concorrente precisa de lock. Fácil de corromper em escritas simultâneas. |
| **`shelve`/`dbm` (stdlib)** | Arquivo(s) DB simples | Nenhuma (stdlib) | Mesma questão de arquivo/volume. | Sem deps. Sem alterações no `requirements.txt`. | API dict-like. Backend `dbm` varia entre sistemas. Menos explícito para schema, menos comum para múltiplas entidades/consultas. |
| **`pickle` (stdlib)** | Arquivo binário `.pkl` | Nenhuma (stdlib) | Mesma questão de arquivo/volume. | Sem deps. Sem alterações no `requirements.txt`. | Frágil entre versões Python, sem integridade/schema, inseguro se carregar fonte não confiável. Não recomendado. |
| **TinyDB** | Arquivo JSON + lib | `tinydb` (pip) | Mesma questão de arquivo/volume. | Adicionar `tinydb` em `requirements.txt`, build instala via pip. Aumenta imagem/camadas. | Conveniente, mas adiciona dependência externa não presente hoje. Desnecessário dado `sqlite3` stdlib. |
| **DuckDB / outros** | Arquivo + lib/binário | Requer wheel/binários extras | Mesma questão de arquivo/volume. | Adiciona deps/binários, aumenta imagem. | Overkill para o caso de uso ("só o catálogo de sequências"). |

## Implicações diretas

### Para o Dockerfile atual (`Dockerfile:1-12`)
- **Sem volume definido:** não há instrução `VOLUME`. Comportamento atual não prevê montagem.
- **Para `sqlite3`/arquivos:** basta criar diretório e gravar em caminho escolhido. Sem alteração obrigatória no Dockerfile se usar `/app/...`, mas persistência entre **recriações** do container dependeria de cópia/volume externo.
- **Para libs externas:** qualquer opção não-stdlib exige adicionar ao `requirements.txt` e rebuild da imagem.

### Para persistência entre reinícios do container
- **`docker stop/start` (mesmo container):** arquivos gravados no filesystem do container persistem independentemente da opção escolhida.
- **`docker rm` + `docker run` (recriação):** filesystem do container é novo. Arquivos criados em tempo de execução **somem** a menos que haja **bind mount** ou **named volume** montado apontando para fora do container. 
- **Imagem reconstruída (`docker build`):** arquivos criados em tempo de execução não ficam na imagem; apenas arquivos copiados por `COPY . .` ficam. Portanto, para "persistir entre reinícios do container" de forma confiável no uso local descrito, é necessário **montar um volume** para o caminho onde o DB/arquivo for salvo.

## Referências
- `docs/adr/0001-local-only-docker-deploy.md:1-24`
- `docs/adr/0002-persist-custom-sequences.md:1-10`
- `docs/features/sequencias-customizadas/01-research.md:39-150`
- `docs/features/sequencias-customizadas/02-proposal.md:1-120`
- `Dockerfile:1-12`
- `requirements.txt:1-6`
- `AGENTS.md:1-60`
- `main.py:1-223`
- `static/templates/sequencia.html:1-80`
- `static/assets/js/controllers/sequencia.js:1-200`
