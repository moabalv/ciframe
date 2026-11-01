# Plano — Sequências de Acordes Customizadas (baseado em 02-proposal.md)

## Contexto
- Feature: CRUD anônimo de sequências customizadas + matching em tempo real para sequências não pré-computadas.
- Abordagem escolhida: SQLite (`sqlite3` stdlib) em `/data/` com volume montado; apenas catálogo vai para o banco (músicas/gêneros continuam em memória via CSV). 
- Matching: contíguo e exato sobre `musica.cifra` (após `limpa_cifra()`), nunca sobre `musica.acordes` (set). Sem replicar exceção CC7FFm (só início). 6 originais continuam em `sequencias` + tag `SEQ_FAMOSA`.
- API: `GET/POST/PUT/DELETE /sequencias`, `GET /similares?sequencia=...` mantido. Respostas via `json.dumps(...)`.
- Frontend: `#/porsequencia` lê catálogo do backend, com cadastro/edição/exclusão.

## Restrições
- Sem novas dependências em `requirements.txt` (usar `sqlite3` stdlib).
- Container único local-only (ADR-0001). Arquivo em `/data/` precisa de volume montado (persiste em `stop/start`, some em recriação sem volume).
- Sem login / anônimo. Quaisquer alterações/exclusões permitidas.
- Sem normalização de acordes.
- Sem rate limiting (fora do escopo).
- Manter testes/regressão das 6 sequências originais.

## Plano de implementação

### 1) Persistência (SQLite)
- [ ] **Criar módulo/estrutura para DB**: adicionar inicialização no startup (`main.py`). Definir caminho (ex. `/data/sequencias_customizadas.db` ou configurável). Criar diretório se não existir.
- [ ] **Schema**: tabela `sequencias_customizadas` com `id INTEGER PRIMARY KEY`, `acordes TEXT UNIQUE NOT NULL`, `criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP`.
- [ ] **Funções**: `init_db()`, `get_all_custom()`, `get_by_id(id)`, `get_by_acordes(acordes_str)`, `create(acordes_str)`, `update(id, acordes_str)`, `delete(id)`. Tratar `UNIQUE` constraint.

### 2) Backend - API `/sequencias`
- [ ] **GET /sequencias**: retornar lista unificada com 6 originais (`origem: 'original'`, `editavel: false`, `id: null`) + customizadas (`origem: 'customizada'`, `editavel: true`, `id: ...`). Manter ordem coerente.
- [ ] **POST /sequencias**: receber `{"acordes": [...]}`. Validar: >= 2 acordes; cada acorde deve existir em `acordes` global (`main.py:77-78`). Se já existir (UNIQUE/lookup), retornar 200 com sequência existente. Senão inserir e retornar 201.
- [ ] **PUT /sequencias/<id>**: validar formato/acordes; checar existência do id (404). Checar duplicata com outro id (409). Atualizar e retornar 200.
- [ ] **DELETE /sequencias/<id>**: checar existência (404). Remover e retornar 200 com id removido.

### 3) Backend - Matching para customizadas
- [ ] **Função helper**: `sequencia_aparece_na_cifra(sequencia_tokens, cifra_da_musica)` (contíguo, igualdade exata). 
- [ ] **Estender `/similares` (`main.py:170-223`)**: se `sequencia_tag` presente, primeiro verificar se está em `sequencias` (6 originais) -> usar fluxo atual `get_similares_por_sequencia`. Senão, verificar se existe no banco de customizadas (normalizar para string concatenada por `,` igual ao formato aceito). Se existir, filtrar `musicas` por gênero via `apply_filtro`, buscar com `sequencia_aparece_na_cifra` em `musica.cifra`, coletar matches. Ordenação: manter ordem da coleção filtrada por gênero (já ordenada por popularidade) conforme proposta. Retornar mesmo formato sem `diferenca`/`intersecao`, paginado via `get_pagina`.
- [ ] **Garantir** uso de `musica.cifra` (nunca `musica.acordes`). Sem replicar regra "só início" para customizadas.

### 4) Frontend (`#/porsequencia`)
- [ ] **sequencia.js**: remover lista hardcoded `sequencia1`-`sequencia4`. Carregar catálogo via `GET /sequencias` no init. Tratar falha: mostrar mensagem de erro (sem fallback fixo).
- [ ] **Formulário de cadastro**: adicionar UI para cadastrar nova sequência (adicionar acordes). Enviar via `POST /sequencias`. Tratar erros 400 e recarregar lista após sucesso.
- [ ] **Edição/Exclusão**: mostrar botões "Editar"/"Excluir" apenas quando `editavel === true`. `PUT /sequencias/<id>` e `DELETE /sequencias/<id>` com confirmação antes de excluir. Recarregar lista após operações.
- [ ] **Busca**: manter fluxo existente com `createChordsString(vm.minhaSequencia.acordes)` para `GET /similares?sequencia=...`. Funcionar para originais e customizadas.
- [ ] **templates/sequencia.html**: atualizar markup para exibir lista dinâmica, formulário de cadastro, botões condicionais.

### 5) Documentação/Deploy
- [ ] **Documentar volume**: adicionar instrução/nota sobre montagem de volume para `/data/` (README ou comentário). Não alterar `Dockerfile` obrigatoriamente se usar caminho existente, mas garantir criação de diretório.
- [ ] **Validar constraints**: confirmar `requirements.txt` sem mudanças.

## Arquivos afetados

| Arquivo | Mudança |
|---|---|
| `main.py` | Adicionar init DB, funções CRUD `/sequencias`, validação de acordes, matching em tempo real para customizadas em `/similares` |
| `musica.py` | Sem mudanças obrigatórias (usar `cifra` existente) |
| `static/assets/js/controllers/sequencia.js` | Carregar catálogo do backend, cadastro/edição/exclusão, remover hardcoded |
| `static/templates/sequencia.html` | UI dinâmica para lista + formulário + botões condicionais |
| (novo) DB file em `/data/sequencias_customizadas.db` | Persistência via SQLite (criado em runtime) |

## Testes / Validação
- [ ] **Regressão**: buscar cada uma das 6 sequências originais via `#/porsequencia` - deve retornar mesmos resultados (tag CSV). 
- [ ] **Cadastro**: cadastrar sequência com >=2 acordes válidos -> 201/200. Tentar cadastrar acorde inválido -> 400. Duplicata -> retorna existente (200).
- [ ] **Matching**: cadastrar `C,G,Am,F` e verificar se encontra músicas com trecho contíguo em `cifra`. Verificar que não usa `acordes` (set). 
- [ ] **Edição/Exclusão**: editar sequência customizada -> busca reflete novo valor. Excluir -> deixa de aparecer/funcionar.
- [ ] **Persistência**: com volume montado, `docker stop/start` mantém; `docker rm` + `docker run` com volume mantém. Sem volume, documentar perda (conforme ADR).
- [ ] **Concorrência básica**: testar com gunicorn (se aplicável) - SQLite deve lidar com transações.

## Definição de pronto
- [ ] Cadastro de sequência funciona (`POST /sequencias`).
- [ ] Busca por sequência cadastrada funciona via `GET /similares?sequencia=...` com matching contíguo em `musica.cifra`.
- [ ] As 6 sequências originais continuam funcionando como antes (regressão validada).
- [ ] Listagem unificada (`GET /sequencias`) mostra originais e customizadas com flags corretas.
- [ ] Edição e exclusão funcionam apenas para customizadas.
- [ ] Persistência em SQLite em `/data/` com volume montado.
- [ ] Validação: >=2 acordes e acordes existentes no CSV.
