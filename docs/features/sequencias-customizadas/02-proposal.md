# Proposta — Sequências de Acordes Customizadas

## Abordagem escolhida

### Algoritmo de matching

Uma música é compatível com uma sequência cadastrada se os acordes da sequência
aparecem **lado a lado e na mesma ordem** em algum ponto de `musica.cifra` (a
lista ordenada, já passada por `limpa_cifra`).

- Uso `musica.cifra` e não `musica.acordes`, porque `acordes` é um conjunto
  (`musica.py:17`) e perde a ordem.
- A comparação é por igualdade exata de cada acorde, sem normalização
  (`C` é diferente de `C7`), igual ao resto do app.
- A sequência pode aparecer em qualquer posição da música e basta uma ocorrência.
- Não replico a exceção da `CC7FFm` (só no início da música) para as sequências
  novas.
- As 6 sequências originais continuam usando a tag `SEQ_FAMOSA` do CSV, então
  os resultados delas não mudam (é o teste de regressão).
- A ordem dos resultados é a mesma das originais: a da coleção filtrada por
  gênero, que já vem ordenada por popularidade.

```python
def sequencia_aparece_na_cifra(sequencia_de_acordes, cifra_da_musica):
    """Retorna True se a sequência aparece como trecho contíguo da cifra."""
    tamanho_da_sequencia = len(sequencia_de_acordes)
    for posicao_inicial in range(len(cifra_da_musica) - tamanho_da_sequencia + 1):
        trecho = cifra_da_musica[posicao_inicial:posicao_inicial + tamanho_da_sequencia]
        if trecho == sequencia_de_acordes:
            return True
    return False
```

### Banco de dados

SQLite, com o módulo `sqlite3` da biblioteca padrão. Só o catálogo de sequências
vai para o banco; músicas e gêneros continuam vindo do CSV em memória.

Escolhi porque não precisa de dependência nova (o `requirements.txt` fica igual),
cabe no container único do ADR-0001, tem transações e esquema explícito, e é mais
seguro que um arquivo JSON caso o gunicorn use mais de um worker. O arquivo fica
em `/data/` e precisa de um volume montado: sem volume os dados sobrevivem a
`docker stop/start`, mas somem se o container for recriado.

### Esquema de dados (alto nível)

Uma tabela, `sequencias_customizadas`:

| Campo | Tipo | Observação |
|---|---|---|
| `id` | inteiro, chave primária | gerado pelo banco |
| `acordes` | texto, `UNIQUE`, não nulo | acordes separados por vírgula, ex.: `C,G,Am,F` (mesmo formato do `?sequencia=`) |
| `criado_em` | timestamp | valor padrão: momento da criação |

A restrição `UNIQUE` em `acordes` impede duplicatas no próprio banco. As 6
originais continuam no dicionário do `main.py` e não entram na tabela.

### API

Sem login: qualquer pessoa pode cadastrar, editar e excluir. Todas as respostas
continuam usando `json.dumps(...)` (string), não `jsonify`.

| Endpoint | Entrada | Saída |
|---|---|---|
| `GET /sequencias` | nenhuma | Lista com as 6 originais e as cadastradas. Cada item tem `acordes`, `origem` (`original` ou `customizada`), `editavel` e `id` (as originais têm `id` nulo e `editavel` falso). |
| `POST /sequencias` | `{"acordes": ["C","G","Am","F"]}` | 201 com a sequência criada. Se já existir, 200 com a sequência que já está no banco. |
| `PUT /sequencias/<id>` | `{"acordes": [...]}` | 200 com a sequência atualizada. 404 se o `id` não existir. 409 se outra sequência já tiver esses acordes. |
| `DELETE /sequencias/<id>` | nenhuma | 200 com o `id` removido. 404 se o `id` não existir. |
| `GET /similares?sequencia=...` | igual a hoje | Mesmo contrato. Se for uma das 6 originais, usa a tag do CSV; senão busca no banco e calcula o matching em `musica.cifra`. |

Validação (POST e PUT, resposta 400 com mensagem): a sequência precisa ter pelo
menos 2 acordes e cada acorde precisa existir no conjunto global `acordes`
montado a partir do CSV (`main.py:77-78`). Acorde fora desse conjunto não casaria
com nenhuma música.

Como as originais não têm `id`, elas não podem ser editadas nem excluídas. Como o
matching das customizadas é calculado na hora, editar ou excluir já vale para as
próximas buscas.

### Frontend

Em `#/porsequencia`:

- O `sequencia.js` deixa de usar a lista hardcoded `sequencia1`..`sequencia4` e
  carrega as sequências de `GET /sequencias`. A página passa a mostrar as 6
  originais e as cadastradas. Se a chamada falhar, mostra uma mensagem de erro,
  sem voltar para uma lista fixa.
- Novo formulário "Cadastrar nova sequência", que envia os acordes para
  `POST /sequencias`. Erros 400 aparecem na tela e, depois de cadastrar, a lista
  recarrega.
- Botões "Editar" (`PUT`) e "Excluir" (`DELETE`) só nas sequências com
  `editavel` verdadeiro, com confirmação antes de excluir.
- A busca continua igual para qualquer sequência, antiga ou nova: chama
  `GET /similares?sequencia=...` e mantém o filtro por gênero.

## Alternativas consideradas e descartadas

- **Arquivo JSON com lock:** descartei porque não tem transações, e um lock em
  Python não protege entre processos se o gunicorn usar mais de um worker. O
  SQLite resolve isso sem dependência nova.
- **Matching por subsequência com saltos:** descartei porque aceitaria músicas em
  que os acordes estão longe um do outro, o que foge da ideia de "sequência" e do
  comportamento atual.
- **Matching contíguo removendo repetições seguidas:** descartei por acrescentar
  uma regra a mais para explicar e testar, sem necessidade comprovada nos dados.

## Escopo explícito

**Dentro do escopo:**

- Cadastrar, listar, editar e excluir sequências anônimas (`POST`, `GET`, `PUT`,
  `DELETE` em `/sequencias`)
- Persistir o catálogo em SQLite, com volume montado
- Matching em tempo real, contíguo e exato sobre `musica.cifra`, para as
  sequências cadastradas
- Validação: mínimo de 2 acordes e só acordes que existem no CSV; duplicata no
  cadastro devolve a sequência existente
- Página `#/porsequencia` lendo o catálogo do backend, com cadastro, edição e
  exclusão
- Teste de regressão das 6 sequências originais

**Fora do escopo (e por quê):**

- **Rate limiting e proteção contra spam:** o catálogo é aberto e anônimo por
  requisito e o app roda só localmente, então o risco é baixo. Fica como
  limitação conhecida.
- **Controle de quem pode editar ou excluir:** sem login não há dono da
  sequência, então qualquer visitante pode alterar ou apagar qualquer sequência
  cadastrada. É consequência do requisito de catálogo anônimo.
- **Normalização de acordes (`C7`, `Cmaj7`):** o app não normaliza hoje e isso
  mudaria o comportamento de todo o matching.
- **Mover as 6 originais para o banco:** elas continuam no `main.py` com a tag do
  CSV para não alterar os resultados de regressão.