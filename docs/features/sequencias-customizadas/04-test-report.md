# Relatório de testes — Sequências de Acordes Customizadas

## Cobertura

**Testes automatizados (unittest)** em `tests/test_sequencias_customizadas.py`:
- `test_get_sequencias_unified` — Verifica GET `/sequencias` retorna lista unificada com 6 originais (`origem:'original'`, `editavel:false`, `id:null`). Valida splits corretos para `BmGDA` (`['Bm','G','D','A']`), `CC7FFm` (`['C','C7','F','Fm']`), `CGAmF` (`['C','G','Am','F']`).
- `test_create_custom_sequence_valid` — Criação válida via POST `/sequencias` com >=2 acordes existentes; retorna `origem:'customizada'`, `editavel:true`, `id` preenchido, `acordes_str` no formato `A,B,...`.
- `test_create_custom_sequence_too_few_chords` — Rejeita com < 2 acordes (400).
- `test_create_custom_sequence_invalid_chord` — Rejeita acorde não pertencente ao conjunto global `acordes` (400).
- `test_create_custom_sequence_duplicate_returns_existing` — Duplicado retorna sequência existente com mesmo `id` e status 200.
- `test_update_custom_sequence` — PUT `/sequencias/<id>` atualiza sequência customizada existente.
- `test_update_nonexistent_returns_404` — PUT em id inexistente retorna 404.
- `test_delete_custom_sequence` — DELETE `/sequencias/<id>` remove sequência customizada; verificado via GET `/sequencias` que não aparece mais.
- `test_delete_nonexistent_returns_404` — DELETE em id inexistente retorna 404.
- `test_custom_sequence_search` — Criação + busca via `/similares?sequencia=...` funciona (fluxo end-to-end).
- `test_regression_original_sequences_match` — **Teste de regressão**: verifica GET `/similares?sequencia=` para todas as 6 originais (`BmGDA`, `CGAmF`, `EmG`, `CA7DmG7`, `GmF`, `CC7FFm`) retorna 200 com lista (mantém comportamento do caminho hardcoded/tag-based).

## Teste de regressão obrigatório

As 6 sequências originais em `main.py:40-45` (`BmGDA`, `CGAmF`, `EmG`, `CA7DmG7`, `GmF`, `CC7FFm`) foram verificadas via `test_regression_original_sequences_match`. 

Resultado: **PASS** (11/11 testes OK). O código mantém o lookup por `sequencias` hardcoded para strings concatenadas exatas e usa `get_similares_por_sequencia` com `musica.seqs_famousas` (comportamento tag-based) - sem replicar a exceção `CC7FFm` "start-only", conforme especificado. Os splits exibidos em `/sequencias` para as originais foram corrigidos para manter acordes multi-caractere intactos (`C7`, `Fm`, `Am`).

## Como rodar

```bash
# Com venv do projeto
cd /home/moab/DevIA/ciframe
SEQ_DB_DIR=/tmp/test_seq_db .venv/bin/python -m unittest tests.test_sequencias_customizadas
```

## O que ficou de fora

- **Testes de UI (AngularJS)**: Não foram adicionados testes automatizados para `sequencia.js`/template (sem framework de teste configurado no projeto). Validação feita manualmente via inspeção de código e fluxo.
- **Persistência entre reinícios em Docker com volume**: Comportamento depende de volume montado em `/data/` (conforme ADR/README). Código usa `SEQ_DB_DIR` com fallback, mas não há teste automatizado para cenário de volume.
- **Ordenação por repetições para customizadas**: Implementado busca contígua em `musica.cifra` para customizadas (conforme proposta), mas não foi adicionado teste específico comparando ordenação - o comportamento segue a lógica implementada.
- **Caso edge CC7FFm com busca customizada**: Não testado criar sequência customizada idêntica a `CC7FFm` e comparar com comportamento tag-based das originais (mantido propositalmente o caminho original para as 6 hardcoded).
