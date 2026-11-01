# Validação da hipótese: matching por sequência famosa

## Hipótese
O matching atual por sequência famosa (`/similares?sequencia=`) não calcula similaridade em tempo real - ele apenas verifica se o `id_seq` mapeado está presente em `musica.seqs_famosas` (pré-computado). 

A hipótese proposta é: reproduzir esse matching em tempo real buscando a **sequência ordenada e contígua** de acordes na lista `Musica.cifra` (após `limpa_cifra()`), contanto ocorrências e ordenando por quantidade de repetições. Ordem importa, repetições importam.

## Metodologia
- Carregar `data/top/dataset_final.csv` usando a mesma lógica do `main.py` (índices 0-8, `limpa_cifra` idêntica)
- Para cada uma das 6 sequências hardcoded em `main.py:40-45`, obter o conjunto "atual" via verificação de `str(seq_id) in seqs_famosas`
- Para cada sequência, buscar ocorrências contíguas e ordenadas em `musica.cifra` com contagem de repetições
- Comparar conjuntos e observar ordenação por repetições

## Mapeamento das sequências
| Sequência | ID | Acordes canônicos |
|-----------|----|--------------------|
| `BmGDA`    | 0  | `['Bm', 'G', 'D', 'A']` |
| `CGAmF`    | 1  | `['C', 'G', 'Am', 'F']` |
| `EmG`      | 2  | `['Em', 'G']` |
| `CA7DmG7`  | 3  | `['C', 'A7', 'Dm', 'G7']` |
| `GmF`      | 4  | `['Gm', 'F']` |
| `CC7FFm`   | 5  | `['C', 'C7', 'F', 'Fm']` |

## Resultados

| Sequência | Atual (count) | Hipótese (count >=1) | Conjuntos iguais | Ordenação por repetições | Observações |
|-----------|----------------|----------------------|------------------|---------------------------|-------------|
| `BmGDA` (0) | 1 | 1 | **Sim** | Mesma única ocorrência | Reprodução exata |
| `CGAmF` (1) | 161 | 161 | **Sim** | Difere da ordem atual (atual não ordena por repetições, segue ordem da coleção filtrada/original) | Reprodução exata do conjunto |
| `EmG` (2) | 4 | 4 | **Sim** | Difere da ordem atual | Reprodução exata do conjunto |
| `CA7DmG7` (3) | 5 | 5 | **Sim** | Difere da ordem atual | Reprodução exata do conjunto |
| `GmF` (4) | 7 | 7 | **Sim** | Difere da ordem atual | Reprodução exata do conjunto |
| `CC7FFm` (5) | 3 | 132 | **Não** | Hipótese retorna 132 músicas com >=1 ocorrência | Comportamento distinto - tag pré-computada é muito mais restritiva |

### Exemplos de matches

**BmGDA (id=0):** `legiao-urbana_pais-e-filhos`

**EmG (id=2):** `eric-clapton_fall-like-rain`, `marcelo-d2_mao-na-cabeca`, `planet-hemp_mao-na-cabeca`, `ultraje-a-rigor_inutil`

**CC7FFm (id=5) - atual:** apenas `claudia-leitte_bem-vindo-amor`, `exaltasamba-musicas_jogo-de-seducao`, `revelacao_jogo-de-seducao`. A hipótese encontra 132 músicas (incluindo muitas outras com a progressão `C, C7, F, Fm` em algum trecho).

## Investigação adicional - caso CC7FFm

Foi verificado que apenas as 3 músicas com a tag `seqs_famosas` contendo `5` têm a sequência `['C','C7','F','Fm']` **no início da cifra** (posição 0):

| Música | Count total | Primeira ocorrência | Tem tag |
|--------|-------------|---------------------|---------|
| `claudia-leitte_bem-vindo-amor` | 12 | pos 0 | Sim |
| `exaltasamba-musicas_jogo-de-seducao` | 15 | pos 0 | Sim |
| `revelacao_jogo-de-seducao` | 7 | pos 0 | Sim |

Das 132 músicas que contêm a sequência em algum lugar, as outras 129 não têm a tag - incluindo `revelacao_jogo-da-seducao` (7 ocorrências) que tem título similar mas não começa com a progressão.

**Hipótese para o critério:** Para `CC7FFm`, o pré-processamento provavelmente aplicou um filtro adicional como **"sequência deve aparecer no início da música"** (ou na progressão principal/intro). Os scripts de geração (`scripts/generate_data_set.py`, `scripts/normalize_chords.R`) provavelmente usaram essa regra mais restritiva para essa sequência específica.

## Conclusões

1. **Para 5 das 6 sequências famosas:** A busca por **substring ordenado e contíguo** na `cifra` processada por `limpa_cifra()` reproduz **exatamente** os mesmos matches que o lookup por `seqs_famosas`. Isso confirma que, na maioria dos casos, a tag pré-computada corresponde à presença dessa progressão ordenada na cifra.
2. **Ordem importa:** Confirmado - buscar em lista ordenada (não em `set`) é necessário. Usar `Musica.acordes` (set) ignoraria ordem e estaria errado.
3. **Repetições:** A hipótese de ordenar por quantidade de ocorrências é razoável para o caso de uso (1.3) - "para o músico talvez não seja tão útil receber uma música que a sequência que ele sabe tocar só aparece uma vez". Porém, **o código atual não ordena por repetições** - ele retorna na ordem da coleção filtrada/original. Qualquer nova implementação que adote ordenação por repetições mudaria a ordenação dos resultados.
4. **Exceção importante - CC7FFm:** A tag pré-computada usa um critério adicional - **a sequência deve aparecer no início da cifra** (posição 0). Não é suficiente aparecer em qualquer ponto da música. Não podemos substituir o lookup por busca textual simples sem replicar esse critério ou entender completamente a regra de geração.

## Recomendação para implementação em tempo real

- **Abordagem viável:** Para sequências customizadas (não as 6 hardcoded), usar busca por substring ordenado e contíguo em `musica.cifra` (lista ordenada após `limpa_cifra`). Considerar ordenar por **número de ocorrências descendente** conforme proposto.
- **Cuidado com compatibilidade:** Manter o comportamento atual das 6 sequências famosas hardcoded (lookup por `seqs_famosas`) ou replicar exatamente seu critério. Não assumir que substring simples é equivalente para todos os casos.
- **Base correta:** Usar `musica.cifra` (lista ordenada), **nunca** `musica.acordes` (que é `set` e perde ordem/repetições).
