# Como funciona o algoritmo de matching para comparar músicas

## Resumo

O algoritmo de matching (semelhança) funciona por **interseção de conjuntos de acordes** com **ordenação por "menor diferença" e "maior interseção"**. Há dois modos principais de busca por similares:

1. **Por acordes/por música base (`/similares` com `acordes` ou `id_unico_musica`)** - comparado por conjunto de acordes únicos.
2. **Por sequência famosa (`/similares` com `sequencia`)** - busca exata por ID de sequência predefinida.

O matching por acordes não considera ordem, frequência/repetições, nem distância entre acordes (apenas presença). A ordenação prioriza músicas com **menor tamanho de diferença** (`len(diff)`) e, em caso de empate, **maior interseção** (`-len(intersecao)`).

## Componentes envolvidos

### `musica.py` (classe `Musica`)
- `self.cifra` = lista de acordes extraída da cifra (após `limpa_cifra` em `main.py:11-23`)
- `self.acordes = list(set(cifra))` (`musica.py:17`) - **conjunto de acordes únicos** (deduplicados). É esse conjunto que é usado para matching e também retornado nas respostas.
- `self.seqs_famosas = seqs_famosas` (`musica.py:18`) - lista com IDs (strings/valores) de sequências famosas presentes na música
- `self.id_unico_musica = '%s_%s' % (id_artista, id_musica)` (`musica.py:20`)
- `self.url = 'http://www.cifraclub.com.br/%s/%s' % (id_artista, id_musica)` (`musica.py:22`)

### `main.py` - carregamento e preparação
- `sequencias` mapeia nomes de sequências para IDs (`main.py:40-45`): `'BmGDA' : 0`, `'CGAmF' : 1`, `'EmG' : 2`, `'CA7DmG7' : 3`, `'GmF' : 4`, `'CC7FFm' : 5`
- Ao carregar CSV (`main.py:49-98`):
  - `musica[CIFRA]` vira lista via `limpa_cifra(musica[CIFRA].split(';'))` se não vazio, senão `[]` (`main.py:58-61`)
  - `musica[SEQ_FAMOSA]` vira lista via `musica[SEQ_FAMOSA].split(";")` (`main.py:63`)
  - Cria `Musica(...)` com `musica[CIFRA]` e `musica[SEQ_FAMOSA]` (`main.py:69-73`)
  - Monta `musicas_dict` por `id_unico_musica` e `musicas` ordenado por popularidade desc (`main.py:74`, `88-89`)
  - Monta `genero_musicas` por gênero (listas ordenadas por popularidade desc em `main.py:95-96`)
  - Monta conjunto global `acordes` com todos os acordes únicos encontrados (`main.py:39`, `77-78`)

### `main.py` - funções de matching
#### `limpa_cifra(raw_cifra)` (`main.py:11-23`)
- Itera sobre cada elemento `m` em `raw_cifra`
- Se vazio: ignora (`main.py:14-15`)
- Se contém `|`: filtra tablatura pegando primeiro token antes de `|` e primeiro espaço: `m.split('|')[0].split()[0]` → adiciona esse acorde (`main.py:16-18`)
- Senão: divide por whitespace e adiciona todos os tokens (`main.py:20-22`)

#### `get_similares(acordes, generos_key, id_musica = None)` (`main.py:230-263`)
- Aplica filtro por gênero via `apply_filtro(musicas.values(), generos_key)` (`main.py:233`). `apply_filtro` concatena listas de `genero_musicas[genero]` para cada gênero em `generos_key` que exista em `generos` (`main.py:266-272`).
- Itera sobre `collection`:
  - Pula se `musica.id_unico_musica == id_musica` (para não retornar a própria música quando buscada por `id_unico_musica`) (`main.py:238-239`)
  - `inter = set(acordes).intersection(set(musica.acordes))` (`main.py:240`)
  - `diff = set(musica.acordes) - set(acordes)` (`main.py:241`) - **diferença = acordes da música candidata que não estão na consulta**
  - Só considera se `len(inter) > 0` (`main.py:245`)
  - Monta objeto com `diferenca` (lista) e `intersecao` (lista), além de metadados (`main.py:246-260`)
- Ordenação final: `sorted(similares, key=lambda x: (len(x['diferenca']), -len(x['intersecao'])))` (`main.py:263`)
  - Critério primário: menor `len(diferenca)` (ascendente)
  - Critério secundário: maior `len(intersecao)` (descendente, por causa do `-`)

#### `get_similares_por_sequencia(id_seq, generos_key)` (`main.py:203-223`)
- Filtra por gênero via `apply_filtro` (`main.py:205`)
- Para cada música na coleção: se `str(id_seq) in musica.seqs_famosas` → adiciona objeto similar com metadados (sem `diferenca`/`intersecao`) (`main.py:209-221`)
- Retorna lista (sem ordenação explícita no código além da ordem resultante da coleção filtrada/original)

### Endpoint `/similares` (`main.py:170-201`)
1. Lê parâmetros: `acordes_tag`, `id_musica_tag`, `sequencia_tag`, `pagina_tag` (default `'1'`), `generos_tag` (opcional) (`main.py:173-183`)
2. Determina `generos_key` = todos os gêneros se não filtrado, senão split por `','` (`main.py:180-183`)
3. **Modo sequência famosa** (`main.py:190-197`):
   - Se `sequencia_tag` presente: `acordes = sequencia_tag.replace(',','')` (linha 191 - variável nomeada `acordes` mas armazena string da sequência)
   - Se `acordes` estiver em `sequencias` (dict mapeando nome->id): obtém `id_seq`, chama `get_similares_por_sequencia(id_seq, generos_key)`, pagina e retorna (`main.py:194-197`)
4. **Modo por acordes/música** (`main.py:199-201`):
   - Se não veio por sequência, constrói `acordes` a partir de: `acordes_tag.split(',')` se presente, ou `musicas[id_musica_tag].acordes` se veio por `id_musica_tag` (`main.py:184-190`)
   - Chama `get_similares(acordes, generos_key, id_musica_tag)`, pagina e retorna (`main.py:199-201`)

### Paginação
- `TAM_PAGINA = 100` (`main.py:35`)
- `get_pagina(colecao, pagina_tag)` fatiamento `(int(pagina_tag)-1)*TAM_PAGINA : sl+TAM_PAGINA` (`main.py:226-228`)

## Fluxo de dados (matching por acordes)
1. Consulta chega via `/similares?acordes=A,B,C` ou `?id_unico_musica=X_Y` (opcional `generos=Rock,Samba`)
2. `musicas[id_musica_tag].acordes` ou split de `acordes_tag` → lista/valores de acordes (da consulta)
3. `apply_filtro` reduz coleção para gêneros solicitados (concatena listas de `genero_musicas`)
4. Para cada candidata (diferente da música base): computa interseção com consulta e diferença (candidata - consulta) usando `set`
5. Mantém apenas com `intersecao > 0`
6. Ordena por `(len(diferenca), -len(intersecao))`
7. Pagina e retorna JSON

## Detalhes importantes (tal como existe hoje)
- **Matching é por conjunto de acordes únicos** (`Musica.acordes = list(set(cifra))` em `musica.py:17`). Repetições de acordes na cifra não afetam o matching nem o tamanho dos conjuntos.
- **Comparação é unidirecional na diferença**: `diff = set(musica.acordes) - set(acordes)` (acordes da candidata não presentes na consulta). Não há métrica simétrica completa explícita no código; a ordenação usa esse `diff` e `intersecao`.
- **Quando buscado por `id_unico_musica`**, a própria música é excluída (`main.py:238-239`), mas usa os `acordes` da própria música como base (`main.py:187-189`).
- **Modo sequência famosa** ignora completamente o cálculo de interseção/diferença - é busca por **membro da lista** `seqs_famosas` correspondente ao ID mapeado (`main.py:194-197`, `203-223`). Resposta não inclui campos `diferenca`/`intersecao`.
- **Filtro por gênero** é feito por concatenação de listas por gênero (`apply_filtro`), com listas já ordenadas por popularidade dentro do gênero (`main.py:95-96`); a ordenação final de `/similares` por acordes é feita apenas por `(len(diferenca), -len(intersecao))` - **popularidade não é critério nessa ordenação final** (ao contrário das listas de `musicas` e `genero_musicas`).
- **`limpa_cifra`** trata tablaturas com `|` extraindo apenas o acorde à esquerda do pipe (`main.py:16-18`), e trata acordes separados por espaço adicionando todos os tokens (`main.py:20-22`). Elementos vazios são ignorados.
