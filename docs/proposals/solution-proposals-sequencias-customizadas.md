## Solution Proposals

**Context:**
- **Request:** Implementar persistência para sequências de acordes customizadas (CRUD anônimo), permitindo que o matching seja feito em tempo real para sequências não pré-computadas, mantendo o modelo local-only com container Docker único.
- **Research Source:** `research/bancos_embarcados_viaveis.md` (seções: "Estado atual relevante", "Bancos embarcados viáveis", "Implicações diretas"). Também utilizado como contexto: `docs/adr/0001-local-only-docker-deploy.md`, `docs/features/sequencias-customizadas/01-research.md`, `main.py:1-223`, `Dockerfile:1-12`, `requirements.txt:1-6`.

---


## Proposal 1 — SQLite com volume montado (padrão recomendado)

### Overview
Utilizar `sqlite3` da biblioteca padrão para persistir apenas o catálogo de sequências customizadas. O banco ficaria em um arquivo (`.db`) fora da camada efêmera do container, montado via volume, com um schema simples para armazenar sequências anônimas. Isso mantém o catálogo de músicas/gêneros vindo do CSV em memória (`main.py:1-100`) e adiciona apenas persistência para o novo recurso.

### Key Changes

| Componente | Mudanças | Referências |
|---|---|---|
| **Banco de dados** | Criar schema minimal (ex: `custom_sequences(id INTEGER PRIMARY KEY, chords TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)`). Armazenar a sequência na forma já usada pelo frontend/backend (concatenada por `,`, compatível com `sequencia_tag.replace(',','')` e com `createChordsString` em `static/assets/js/controllers/sequencia.js:118-123`). | `research/bancos_embarcados_viaveis.md:56-90`, `main.py:170-223`, `static/assets/js/controllers/sequencia.js:118-123` |
| **Backend (`main.py`)** | Adicionar inicialização do SQLite no startup (conexão/`CREATE TABLE IF NOT EXISTS`), funções de CRUD anônimo (create/list/get). Estender `/similares` (`main.py:170-223`) para: (1) manter comportamento atual para `acordes`/`id_unico_musica` e para sequências hardcoded presentes em `sequencias` (`main.py:40-45`) via `get_similares_por_sequencia`; (2) caso `sequencia_tag` não esteja em `sequencias`, buscar a sequência no banco de sequências customizadas (por string concatenada sem vírgulas ou pela representação armazenada) e, se encontrada, **calcular matching em tempo real**. Para sequências customizadas, aplicar **matching por substring ordenado e contíguo sobre `musica.cifra`** (lista ordenada após `limpa_cifra()` em `main.py:11-23`), **nunca sobre `musica.acordes`** (set em `musica.py:17`). A busca deve considerar ocorrências contíguas da sequência de tokens na ordem. **Ordenação**: conforme hipótese validada, pode-se ordenar por número de ocorrências da sequência na `cifra` (desc), pois repetições importam para o caso de uso; no entanto, manter coerência com o fato de que o código atual não ordena por repetições - documentar comportamento. **Não replicar** o critério "apenas no início" do CC7FFm para sequências customizadas (seguindo validação: apenas 5/6 reproduzíveis por busca em qualquer lugar). Adicionar endpoints `POST /sequencias` (CRUD anônimo, cria sequência) e `GET /sequencias` (lista) se necessário, sem alterar contrato dos endpoints existentes de forma quebrante. | `main.py:11-23, 40-45, 170-223`, `musica.py:17`, `research/validacao_hipotese_sequencias_famosas.md:1-80`, `research/matching_algorithm.md` |
| **Docker/Deploy** | Definir caminho persistente (ex: `/data/custom_sequences.db`). Criar diretório no container (`RUN mkdir -p /data`). Documentar montagem de volume (bind mount ou named volume) para persistência entre recriações. **Não adicionar dependências** ao `requirements.txt`. | `Dockerfile:1-12`, `requirements.txt:1-6`, `research/bancos_embarcados_viaveis.md:80-95`, `docs/adr/0001-local-only-docker-deploy.md:1-24` |
| **Frontend** | Estender `static/assets/js/controllers/sequencia.js`: substituir lista hardcoded `sequencia1`-`sequencia4` por carga dinâmica via `GET /sequencias` (fallback para hardcoded se falhar). Adicionar UI para cadastro anônimo (input para adicionar nova sequência de acordes). Ao pesquisar, manter envio via `createChordsString(vm.minhaSequencia.acordes)` para `similares?sequencia=...` (compatível com parsing atual). Em `static/templates/sequencia.html`, adicionar seção para "Cadastrar nova sequência" (botão/adicionar acordes) além da lista de sequências famosas/customizadas. Preservar comportamento existente de filtro por gênero e navegação para letras. | `static/assets/js/controllers/sequencia.js:1-200`, `static/templates/sequencia.html:1-80`, `docs/features/sequencias-customizadas/01-research.md:95-110` |

### Algoritmo de matching (detalhado)

1. **Extração da sequência**: receber `sequencia_tag` (string com acordes separados por `,` vindo do frontend via `createChordsString`), converter para lista ordenada de tokens `seq_tokens = [t.strip() for t in sequencia_tag.split(',')]`. 
2. **Normalização**: **não aplicar** normalização case/variante/enharmônica hoje (conforme `research/matching_algorithm.md` - nenhuma normalização existe no app). Usar comparação exata por token igual ao que vem da cifra após `limpa_cifra()`.
3. **Base de busca**: iterar sobre `musicas` filtradas por gênero (`apply_filtro`), usar **`musica.cifra`** (lista ordenada). **Nunca** usar `musica.acordes` (conjunto). 
4. **Ocorrências**: encontrar todas as posições `i` onde `musica.cifra[i : i+len(seq_tokens)] == seq_tokens` (substring ordenado e contíguo). Contar `count = número de ocorrências`.
5. **Critério**: música é compatível se `count >= 1`. Para sequências customizadas **não aplicar** filtro "apenas início" (diferente do caso CC7FFm pré-computado). 
6. **Ordenação**: ordenar resultados por `( -count, -musica.popularidade )` ou similar, considerando que repetições importam (hipótese validada). Caso seja necessário manter compatibilidade estrita com ordenação atual, documentar trade-off; porém o objetivo é melhor UX para sequências customizadas.
7. **Retorno**: mesmo formato dos resultados existentes (`id_unico_musica`, artista/música, popularidade, acordes, genero, url) - sem `diferenca`/`intersecao` (igual a `get_similares_por_sequencia`), paginados via `get_pagina`.

### Trade-offs

| Benefícios | Riscos |
|---|---|
| **Sem dependências novas** - usa `sqlite3` stdlib. | **Requer volume** para persistir entre recriações do container (`docker rm/run`). Sem volume, dados somem. |
| **Robusto** - ACID, transações, schema explícito, prevene corrupção com escrita concorrente melhor que arquivo texto puro. | **Necessita disciplina de path** - precisa garantir diretório com permissão e documentação da montagem. |
| **Alinhado à arquitetura** - "só o catálogo de sequências vai para o banco", músicas/gêneros continuam em memória via CSV. | **Pouco mais complexo** que arquivo JSON (migrations simples, mas ainda necessárias). |
| **Fácil de inspecionar/localizar** em uso local. | **Overhead mínimo** aceitável para volume pequeno de sequências anônimas. |

### Validation

| Tipo | Ação | Critério de sucesso |
|---|---|---|
| **Persistência** | `docker run` com volume montado, criar sequência via API/frontend, `docker stop/start` mesmo container; depois `docker rm` + `docker run` com mesmo volume. | Sequência criada persiste em ambos os cenários. |
| **Concorrência** | Testar com múltiplos requests simultâneos de criação/busca (gunicorn workers). | Sem corrupção de banco; transações evitam race conditions básicas. |
| **Matching** | Validar contra `research/validacao_hipotese_sequencias_famosas.md` - para sequências customizadas, buscar por substring ordenado/contíguo em `musica.cifra` (após `limpa_cifra`). Testar caso similar ao CC7FFm (apenas início) **não** deve ser replicado - manter comportamento apenas onde necessário, mas matching novo deve seguir regra "aparece em qualquer lugar" conforme hipótese validada exceto exceção pré-existente documentada. | Resultados corretos para sequências customizadas; não quebra matching de sequências famosas existentes. |
| **Integridade** | Verificar que `requirements.txt` permanece inalterado e imagem builda com `python:3.9-slim`. | Build sem novas deps. |

### Open Questions
- **Caminho padrão**: usar `/data/` (fora de `/app`) ou `/app/data/`? Melhor fora para deixar claro que é volume montado.
- **Schema exato**: armazenar como string concatenada por `,` (igual ao parâmetro `sequencia`) ou JSON array? Precisa ser compatível com parsing atual.
- **Autenticação/limites**: CRUD anônimo - precisa rate-limiting? (não mencionado na pesquisa, mas relevante para local-only aberto)
- **Backup/migração**: como migrar dados entre versões? (schema simples facilita)


---


## Proposal 2 — Arquivo JSON com lock (100% stdlib, sem mudanças no Dockerfile)

### Overview
Persistir sequências customizadas em um arquivo JSON único (ex: `/app/data/custom_sequences.json` ou caminho configurável). Utilizar lock de arquivo (`fcntl`/`msvcrt` ou `threading.RLock` + escrita atômica) para mitigar acesso concorrente. Totalmente baseado em stdlib, sem adicionar dependências. Alinhado com "sem serviço externo adicional" e com o menor impacto ao `Dockerfile` atual.

### Key Changes

| Componente | Mudanças | Referências |
|---|---|---|
| **Persistência** | Criar estrutura `{"sequences": [{"id": "...", "chords": ["C","G","Am","F"], "created_at": "..."}]}`. Armazenar também representação concatenada `chords_str = ",".join(chords)` para compatibilidade com parsing atual. Leitura/escrita com lock e escrita atômica (escrever em arquivo temporário + `os.replace`). | `research/bancos_embarcados_viaveis.md:56-90`, `static/assets/js/controllers/sequencia.js:118-123` |
| **Backend (`main.py`)** | Adicionar helpers para carregar/salvar JSON com lock (protegendo contra escritas concorrentes; notar limitação entre processos com gunicorn). Carregar em memória no startup e manter cache sincronizado. Endpoints CRUD anônimo (`POST /sequencias`, `GET /sequencias`). Estender `/similares` (`main.py:170-223`) para buscar sequências customizadas além de `sequencias` hardcoded. Aplicar **mesmo algoritmo de matching**: substring ordenado e contíguo sobre `musica.cifra` (após `limpa_cifra()`), nunca sobre `musica.acordes` (set), contagem de ocorrências para ordenação (desc), sem replicar critério "apenas início" do CC7FFm. | `main.py:11-23, 40-45, 170-223`, `musica.py:17`, `research/validacao_hipotese_sequencias_famosas.md:1-80` |
| **Docker/Deploy** | **Sem alterações obrigatórias no `Dockerfile`**. Se arquivo ficar em `/app/` e container for recriado sem volume, dados somem - precisa documentar montagem. Caminho deve ser configurável via env var. | `Dockerfile:1-12`, `requirements.txt:1-6`, `research/bancos_embarcados_viaveis.md:80-95` |
| **Frontend** | Mesma abordagem que Proposal 1: carregar sequências customizadas via `GET /sequencias`, permitir cadastro anônimo, manter envio via `createChordsString` para `GET /similares?sequencia=...`. Ajustes em `static/assets/js/controllers/sequencia.js` e `static/templates/sequencia.html`. | `static/assets/js/controllers/sequencia.js:1-200`, `static/templates/sequencia.html:1-80` |

### Algoritmo de matching (detalhado)
Mesma especificação da Proposal 1:
1. Parsear `sequencia_tag` para lista ordenada de tokens.
2. Comparação exata (sem normalização).
3. Buscar em `musica.cifra` (ordenada) com substring contíguo, contar ocorrências.
4. Compatível se `count >= 1` (sem filtro "início" para customizadas).
5. Ordenar por `-count` (e opcionalmente popularidade) - consistente com hipótese de repetições importarem.
6. Retornar mesmo formato paginado.

### Trade-offs

| Benefícios | Riscos |
|---|---|
| **Zero novas dependências** - apenas stdlib (`json`, `os`, `fcntl`/`threading`). `requirements.txt` intacto. | **Sem ACID/transações** - escrita atômica reduz risco, mas não garante integridade em todos os cenários. |
| **Menor impacto no Dockerfile** - não exige criar diretório fora do padrão se usar `/app/`. | **Concorrência problemática** - gunicorn com múltiplos workers/processos: lock entre threads não protege entre processos. Em uso local com 1 worker pode ser ok, mas não é garantido. |
| **Fácil de debugar/editar manualmente** - arquivo JSON legível. | **Escalabilidade/robustez** - sem schema, sem constraints, fácil de corromper. |
| **Rápido para prototipar**. | **Persistência frágil entre recriações** - se mantido em `/app/` sem volume, some ao recriar container (mesmo problema, mas mais tentador a não usar volume). |

### Validation

| Tipo | Ação | Critério de sucesso |
|---|---|---|
| **Persistência** | Testar com volume montado para o diretório do JSON. Criar sequência, `stop/start` e recriação com volume. | Persiste com volume; comportamento sem volume documentado como não-persistente. |
| **Concorrência** | Simular escritas simultâneas com múltiplos workers. | Sem corrupção visível; idealmente com lock + escrita atômica. Documentar limitação se não totalmente seguro. |
| **Matching** | Mesma validação que Proposal 1 - matching em tempo real sobre `musica.cifra` para sequências customizadas. | Correto; não quebra sequências famosas. |
| **Recuperação** | Testar arquivo JSON malformado (backup/cópia). | Aplicação deve falhar graciosamente ou reverter para estado vazio com log claro. |

### Open Questions
- **Suporte a multi-worker**: é necessário garantir segurança entre processos? Se sim, precisa de lock inter-processo robusto.
- **Localização do arquivo**: forçar uso com volume ou aceitar perda em recriação?
- **Limites**: sem DB, consultas mais complexas (futuro) ficam mais difíceis.
- **Compatibilidade de paths**: garantir escrita em ambiente Docker (`/app` vs volume).


---


## Comparação direta com a pesquisa

- **Ambas propostas seguem a constraint**: sem serviço externo, cabem em container único local-only (`Dockerfile` atual sem mudanças estruturais obrigatórias para proposta 2, mínimas para proposta 1). 
- **Persistência**: pesquisa deixa claro que **sem volume montado os dados somem entre recriações** - ambas exigem volume para persistência confiável entre `docker rm/run`. 
- **Matching**: grounded em `research/validacao_hipotese_sequencias_famosas.md` - ordem importa, usar `musica.cifra` (não `musica.acordes` set), repetições podem ser consideradas para ordenação mas não replicar exceção CC7FFm (`posição 0`) para sequências customizadas.
- **Escopo**: apenas catálogo de sequências vai para persistência, músicas/gêneros permanecem em CSV em memória (`main.py:1-100`).

**Recomendação baseada na pesquisa:** **Proposal 1 (SQLite + volume)** é mais alinhado com robustez, concorrência com gunicorn e evolução futura, sem adicionar dependências.
