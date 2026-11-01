# Pesquisa — Sequências de Acordes Customizadas

## Perguntas que você precisa responder

1. **Algoritmo de matching**: hoje, as 6 sequências hardcoded em `main.py` (linhas
   40-45) são comparadas contra músicas via uma tag pré-computada
   (`SEQ_FAMOSA`/`seqs_famosas`, vinda do CSV). Sequências cadastradas pelo usuário
   não têm essa tag — o matching precisa ser calculado em tempo real a partir da
   lista de acordes de cada música (`musica.acordes`/`musica.cifra`). O que vai
   definir "a sequência X aparece na música Y"? A ordem dos acordes importa?
   Repetições de acorde dentro da música importam? É preciso normalizar (ex.:
   maiúsculas/minúsculas, variações de escrita do mesmo acorde)?
2. **Validação da hipótese**: rode o algoritmo que você está considerando contra os
   dados reais em `data/top/dataset_final.csv`, para as 6 sequências hoje
   hardcoded, e confirme (ou refute) que ele reproduz os mesmos matches que o
   código atual produz via `seqs_famosas`. Esse é o bar mínimo de correção que
   você vai usar na fase de testes.
3. **Banco de dados**: quais bancos embarcados (sem serviço externo adicional) são
   viáveis dentro do container Docker único e local-only já documentado em
   `docs/adr/0001-local-only-docker-deploy.md`? O que cada opção implica para o
   `Dockerfile` atual e para a persistência dos dados entre reinícios do
   container?
4. **Frontend existente**: o que a página `#/porsequencia`
   (`static/templates/sequencia.html` +
   `static/assets/js/controllers/sequencia.js`) já faz? Repare que ela tem hoje uma
   lista *hardcoded no JavaScript* de 4 sequências (`sequencia1`..`sequencia4`),
   diferente das 6 que existem no backend — um detalhe real e pré-existente do
   código, não um erro seu, que vale entender antes de decidir o que precisa
   mudar.

## Registro das descobertas

[Para cada pergunta acima: o que você encontrou, com referência de onde (arquivo,
linha, documentação, teste que você rodou).]

### Algoritmo de matching
Para responder usei tanto minha percepção pessoal do assunto quanto partes do código. usei o research para ver como é feito atualmente o matching em research/matching_algorithm.md

1.1 Hoje o sistema não calcula nenhum matching de sequência: ele só procura o id da sequência numa tag pré-computada no CSV (cujo critério de geração é desconhecido)

1.2 A ordem dos acordes importa? No matching por acordes (get_similares), não: ele usa interseção e diferença entre conjuntos (main.py:240-241) sobre Musica.acordes = list(set(cifra)) (musica.py:17). Mas no matching de sequência a ordem importa, pois considera que você sabe tocar os acordes e a transição de um acorde para o outro.

1.3 Repetições dentro da música importam? Vamos ordernar o retorno pela quantidade de repetições. Para o músico talvez não seja tão útil receber uma música que a sequência que ele sabe tocar só aparece uma vez.

### Validação da hipótese

Após a execução de um algoritmo que considera a a presença da sequência em ordem. A hipótese foi praticamente validade. Conforme as conclusões abaixo. O relatório completo está em research/validacao_hipotese_sequencias_famosas.md

#### Conclusões

1. **Para 5 das 6 sequências famosas:** A busca por **substring ordenado e contíguo** na `cifra` processada por `limpa_cifra()` reproduz **exatamente** os mesmos matches que o lookup por `seqs_famosas`. Isso confirma que, na maioria dos casos, a tag pré-computada corresponde à presença dessa progressão ordenada na cifra.
2. **Ordem importa:** Confirmado - buscar em lista ordenada (não em `set`) é necessário. Usar `Musica.acordes` (set) ignoraria ordem e estaria errado.
3. **Repetições:** A hipótese de ordenar por quantidade de ocorrências é razoável para o caso de uso (1.3) - "para o músico talvez não seja tão útil receber uma música que a sequência que ele sabe tocar só aparece uma vez". Porém, **o código atual não ordena por repetições** - ele retorna na ordem da coleção filtrada/original. Qualquer nova implementação que adote ordenação por repetições mudaria a ordenação dos resultados.
4. **Exceção importante - CC7FFm:** A tag pré-computada usa um critério adicional - **a sequência deve aparecer no início da cifra** (posição 0). Não é suficiente aparecer em qualquer ponto da música.

DO meu ponto de vista, a exceção do CC7FFm foi algo considerado por quem gerou as similidades e não deve ser considerado como um parâmetro a mais de filtro.

### Banco de dados

Hoje o projeto não tem banco de dados: main.py carrega data/top/dataset_final.csv em memória no import, e o deploy é um Dockerfile único (python:3.9-slim, gunicorn na porta 8080) sem VOLUME e sem serviços externos (ADR-0001; Dockerfile:1-12; requirements.txt:1-6). Dentro dessa restrição, as opções viáveis são todas baseadas em arquivo local. O SQLite (sqlite3 da biblioteca padrão) não exige nova dependência nem mudança obrigatória no Dockerfile e oferece SQL, transações e esquema explícito. O JSON puro e o shelve/dbm também dependem apenas da stdlib, mas não têm transações nativas e exigem controle de escrita concorrente com mais de um worker do gunicorn, e o pickle é frágil entre versões e não recomendado. TinyDB e DuckDB exigem adicionar dependências e rebuild da imagem, o que é desnecessário para um catálogo pequeno. Em todas as opções a persistência segue a mesma regra: os dados sobrevivem a docker stop/start do mesmo container, mas se perdem em docker rm + docker run ou rebuild da imagem, a menos que o arquivo fique em um bind mount ou named volume (ex.: -v ./data:/data). Portanto, o requisito de persistir entre reinícios implica montar um volume, independentemente do formato escolhido.

### Front-end atual
Atualmente tem 4 sequências de acordes que ao serem clicados mostram as músicas que teve o matching. Também é possível filtrar as músicas por gênero. Não dá pra ver quantas vezes a sequência aparece na música. Também não dá pra cadastrar uma nova sequência.

## Trade-offs identificados

[Opções reais que você considerou para cada decisão (algoritmo, banco, frontend) e
os prós/contras de cada uma. Isso alimenta a fase de proposta — não decida ainda
aqui.]

Para o algoritmo, considerei deixar o usuário escolher se precisa de repetição ou não, mas achei mais viável ordenar pela quantidade de vezes que a sequência aparece. Assim, o usuário vê primeiro músicas que de fato ele vai conseguir aproveitar mais a sequência que ele sabe.
Considerei dar a opção de ser a sequência de início, mas pode ser uma feature de uso muito específico.

Para o banco de dados, consideirei o SQLite que não exigiria uma mudança no dockerfile apenas nos requirements. 
Pensei em guardar num json mas seria inseguro contra concorrência

Sobre o front-end a ideia é deixar próximo do que é hoje. Mas adicionar quantas vezes a sequência aparece na música e adicionar a adição de novas sequências.