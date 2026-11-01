# coding: utf-8
import json
from flask import Flask, request
import sys
from musica import *
from collections import OrderedDict
import unicodedata
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB_DIR = os.environ.get('SEQ_DB_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
DB_PATH = os.path.join(DB_DIR, 'sequencias_customizadas.db')


def init_db():
    global DB_DIR, DB_PATH
    try:
        os.makedirs(DB_DIR, exist_ok=True)
    except Exception:
        pass
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS sequencias_customizadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acordes TEXT UNIQUE NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        conn.close()
        return
    except Exception:
        pass
    # fallback
    try:
        alt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        os.makedirs(alt_dir, exist_ok=True)
        DB_DIR = alt_dir
        DB_PATH = os.path.join(DB_DIR, 'sequencias_customizadas.db')
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS sequencias_customizadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acordes TEXT UNIQUE NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_custom_sequences():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT id, acordes, criado_em FROM sequencias_customizadas ORDER BY id')
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({'id': r['id'], 'acordes': r['acordes']})
    return result


def get_custom_by_id(seq_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT id, acordes FROM sequencias_customizadas WHERE id = ?', (seq_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {'id': row['id'], 'acordes': row['acordes']}


def get_custom_by_acordes(acordes_str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT id, acordes FROM sequencias_customizadas WHERE acordes = ?', (acordes_str,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {'id': row['id'], 'acordes': row['acordes']}


def create_custom_sequence(acordes_str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO sequencias_customizadas (acordes) VALUES (?)', (acordes_str,))
        conn.commit()
        seq_id = cur.lastrowid
        conn.close()
        return {'id': seq_id, 'acordes': acordes_str}, 201
    except sqlite3.IntegrityError:
        conn.close()
        existing = get_custom_by_acordes(acordes_str)
        if existing:
            return existing, 200
        return None, 409
    except Exception:
        conn.close()
        return None, 500


def update_custom_sequence(seq_id, acordes_str):
    existing_by_id = get_custom_by_id(seq_id)
    if not existing_by_id:
        return None, 404
    # check duplicate
    dup = get_custom_by_acordes(acordes_str)
    if dup and dup['id'] != int(seq_id):
        return None, 409
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('UPDATE sequencias_customizadas SET acordes = ? WHERE id = ?', (acordes_str, seq_id))
        conn.commit()
        conn.close()
        return {'id': int(seq_id), 'acordes': acordes_str}, 200
    except sqlite3.IntegrityError:
        conn.close()
        return None, 409
    except Exception:
        conn.close()
        return None, 500


def delete_custom_sequence(seq_id):
    existing_by_id = get_custom_by_id(seq_id)
    if not existing_by_id:
        return None, 404
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM sequencias_customizadas WHERE id = ?', (seq_id,))
        conn.commit()
        conn.close()
        return {'id': int(seq_id)}, 200
    except Exception:
        conn.close()
        return None, 500


init_db()

def limpa_cifra(raw_cifra):
    cifra = []
    for m in raw_cifra:
        if m.strip() != '':
            # filtra tablaturas
            if '|' in m:
                acorde = m.split('|')[0].split()[0]
                cifra.append(acorde)
            # lida com acordes separados por espaço
            else:
                tokens = [token for token in m.split()]
                cifra += tokens
    return cifra

# colunas do csv
ARTISTA_ID = 0
MUSICA_ID = 1
ARTISTA = 2
MUSICA = 3
GENERO = 4
POPULARIDADE = 5
TOM = 6
SEQ_FAMOSA = 7
CIFRA = 8
TAM_PAGINA = 100

genero_musicas = {}
generos = set()
acordes = set()
sequencias = {'BmGDA' : 0,
        'CGAmF' : 1,
        'EmG' : 2,
        'CA7DmG7' : 3,
        'GmF' : 4,
        'CC7FFm' : 5}

musicas_dict = {}

f = open('data/top/dataset_final.csv')
f.readline()

for line in f:
    line = line.replace('"', '').replace('NA', '')[:-1]

    musica = line.split(',')
    musica[POPULARIDADE] = int(musica[POPULARIDADE].replace('.', ''))

    if musica[CIFRA] != '':
        musica[CIFRA] = limpa_cifra(musica[CIFRA].split(';'))
    else:
        musica[CIFRA] = []

    musica[SEQ_FAMOSA] = musica[SEQ_FAMOSA].split(";")

    # conjunto único de gêneros
    generos.add(musica[GENERO])

    # inclui música no dict de músicas
    musica_obj = Musica(musica[ARTISTA_ID], musica[ARTISTA],
            musica[MUSICA_ID], musica[MUSICA], musica[GENERO],
            int(musica[POPULARIDADE]), musica[SEQ_FAMOSA],
            musica[TOM], musica[CIFRA])

    musicas_dict[musica_obj.id_unico_musica] = musica_obj

    # conjunto único de acordes
    for acorde in musica_obj.acordes:
        acordes.add(acorde)

    # constrói dict mapeando gênero para músicas
    # deve ser usado para melhorar o desempenho das buscas
    if musica_obj.genero in genero_musicas:
        genero_musicas[musica_obj.genero].append(musica_obj)
    else:
        genero_musicas[musica_obj.genero] = [musica_obj]

# dicionário de músicas cujos valores são ordenados por popularidade
musicas = OrderedDict(sorted(musicas_dict.items(),
    key=lambda x: x[1].popularidade, reverse = True))

# para trabalhar melhor com json
generos = list(generos)

# ordena genero_musicas por popularidade
for k,v in genero_musicas.items():
    genero_musicas[k].sort(key = lambda x : x.popularidade, reverse = True)

f.close()


@app.route('/')
def index():
    return app.send_static_file('index.html')
''' Busca por músicas que possuem no título ou no nome do artista o argumento passado por key.
params: key e generos (opcional). Caso generos não sejam definidos, a busca não irá filtrar por gênero.
exemplo 1: /search?key=no dia em que eu saí de casa
exemplo 2: /search?key=no dia em que eu saí de casa&generos=Rock,Samba '''

@app.route('/<path:path>')
def static_proxy(path):
  # send_static_file will guess the correct MIME type
  return app.send_static_file(path)

@app.route('/search')
def busca():
    generos_tag = request.args.get('generos', [])
    pagina_tag = request.args.get('pagina','1')
    keys = request.args.get('key').lower()
    keys = remover_combinantes(keys).split(' ')

    generos_key = generos
    if generos_tag:
        generos_key = generos_tag.split(',')

    collection = apply_filtro(musicas.values(), generos_key)
    out = []

    for musica in collection:
        text = '%s %s' % (musica.nome_artista.lower(), musica.nome_musica.lower())
        text_list = remover_combinantes(text).split(' ')
        if all(key in text_list for key in keys):
            matches = {
                'id_unico_musica' : musica.id_unico_musica,
                'id_artista' : musica.id_artista,
                'id_musica' : musica.id_musica,
                'nome_artista' : musica.nome_artista,
                'nome_musica' : musica.nome_musica,
                'genero' : musica.genero,
                'url' : musica.url,
            }
            out.append(matches)
    return json.dumps(get_pagina(out, pagina_tag))

# cópia
def remover_combinantes(string):
    string = unicodedata.normalize('NFD', string)
    return u''.join(ch for ch in string if unicodedata.category(ch) != 'Mn')

''' Retorna as músicas armazenadas no sistema (ordenados por popularidade).
    O serviço é paginado. Cada página tem tamanho 100, por default.
    params: pagina. Caso não seja definida a página, o valor default é 1.
    exemplo 1: /musica?pagina=2
    exemplo 2: /musica'''
@app.route('/musicas')
def get_musicas():
    return json.dumps([v.__dict__ for v in musicas.values()])

@app.route('/generos')
def get_generos():
    return json.dumps(generos)

@app.route('/acordes')
def get_acordes():
    return json.dumps(list(acordes))

@app.route('/musica/<m_id>/')
def get_musica(m_id):
    return json.dumps(musicas[m_id].__dict__)

def sequencia_aparece_na_cifra(sequencia_tokens, cifra_da_musica):
    if not sequencia_tokens or not cifra_da_musica:
        return False
    tamanho_da_sequencia = len(sequencia_tokens)
    if tamanho_da_sequencia > len(cifra_da_musica):
        return False
    for posicao_inicial in range(len(cifra_da_musica) - tamanho_da_sequencia + 1):
        trecho = cifra_da_musica[posicao_inicial:posicao_inicial + tamanho_da_sequencia]
        if trecho == sequencia_tokens:
            return True
    return False


def split_concatenated_chords(s):
    if not s:
        return []
    result = []
    i = 0
    chords_list = sorted(list(acordes), key=len, reverse=True)
    while i < len(s):
        matched = None
        # try to find longest matching chord from known set
        for c in chords_list:
            if s.startswith(c, i):
                # make sure we don't cut in middle of something odd - prefer longest
                matched = c
                break
        if matched:
            result.append(matched)
            i += len(matched)
            continue
        # fallback heuristics
        # check 2-char
        if i + 1 < len(s):
            cand2 = s[i:i+2]
            if cand2 in acordes:
                result.append(cand2)
                i += 2
                continue
        if i + 1 < len(s) and s[i+1] in ['m', '#', 'b', '7', '9']:
            # try to extend a bit
            if i + 2 < len(s) and s[i+2] in ['7', '9', '0', 'm']:
                cand3 = s[i:i+3]
                if cand3 in acordes:
                    result.append(cand3)
                    i += 3
                    continue
            cand2 = s[i:i+2]
            result.append(cand2)
            i += 2
            continue
        result.append(s[i])
        i += 1
    return result


@app.route('/sequencias', methods=['GET', 'POST'])
def sequencias_endpoint():
    if request.method == 'GET':
        # build unified list
        result = []
        # add originals - use known correct splits
        original_splits = {
            'BmGDA': ['Bm', 'G', 'D', 'A'],
            'CGAmF': ['C', 'G', 'Am', 'F'],
            'EmG': ['Em', 'G'],
            'CA7DmG7': ['C', 'A7', 'Dm', 'G7'],
            'GmF': ['Gm', 'F'],
            'CC7FFm': ['C', 'C7', 'F', 'Fm'],
        }
        for seq_str, seq_id in sequencias.items():
            acordes_list = original_splits.get(seq_str) or split_concatenated_chords(seq_str)
            result.append({
                'acordes': acordes_list,
                'acordes_str': seq_str,
                'origem': 'original',
                'editavel': False,
                'id': None
            })
        # add custom
        customs = get_custom_sequences()
        for c in customs:
            result.append({
                'acordes': c['acordes'].split(',') if c['acordes'] else [],
                'acordes_str': c['acordes'],
                'origem': 'customizada',
                'editavel': True,
                'id': c['id']
            })
        return json.dumps(result)
    elif request.method == 'POST':
        try:
            data = request.get_json(force=True, silent=True) or {}
        except Exception:
            data = {}
        acordes_list = data.get('acordes') or []
        if not isinstance(acordes_list, list):
            return json.dumps({'erro': 'acordes deve ser uma lista'}), 400
        if len(acordes_list) < 2:
            return json.dumps({'erro': 'sequencia precisa ter pelo menos 2 acordes'}), 400
        # validate each chord exists in global acordes set
        for ac in acordes_list:
            if ac not in acordes:
                return json.dumps({'erro': 'acorde nao existe no conjunto de acordes'}), 400
        acordes_str = ','.join([str(a).strip() for a in acordes_list])
        res, status = create_custom_sequence(acordes_str)
        if status == 201 and res:
            return json.dumps({'id': res['id'], 'acordes': res['acordes'].split(',') if res['acordes'] else [], 'acordes_str': res['acordes'], 'origem': 'customizada', 'editavel': True}), 201
        elif status == 200 and res:
            return json.dumps({'id': res['id'], 'acordes': res['acordes'].split(',') if res['acordes'] else [], 'acordes_str': res['acordes'], 'origem': 'customizada', 'editavel': True}), 200
        elif status == 409:
            return json.dumps({'erro': 'conflito'}), 409
        else:
            return json.dumps({'erro': 'erro ao criar'}), 500


@app.route('/sequencias/<int:seq_id>', methods=['PUT', 'DELETE'])
def sequencia_detail(seq_id):
    if request.method == 'PUT':
        try:
            data = request.get_json(force=True, silent=True) or {}
        except Exception:
            data = {}
        acordes_list = data.get('acordes') or []
        if not isinstance(acordes_list, list):
            return json.dumps({'erro': 'acordes deve ser uma lista'}), 400
        if len(acordes_list) < 2:
            return json.dumps({'erro': 'sequencia precisa ter pelo menos 2 acordes'}), 400
        for ac in acordes_list:
            if ac not in acordes:
                return json.dumps({'erro': 'acorde nao existe no conjunto de acordes'}), 400
        acordes_str = ','.join([str(a).strip() for a in acordes_list])
        res, status = update_custom_sequence(seq_id, acordes_str)
        if status == 200 and res:
            return json.dumps({'id': res['id'], 'acordes': res['acordes'].split(',') if res['acordes'] else [], 'acordes_str': res['acordes'], 'origem': 'customizada', 'editavel': True}), 200
        elif status == 404:
            return json.dumps({'erro': 'nao encontrado'}), 404
        elif status == 409:
            return json.dumps({'erro': 'conflito'}), 409
        else:
            return json.dumps({'erro': 'erro ao atualizar'}), 500
    elif request.method == 'DELETE':
        res, status = delete_custom_sequence(seq_id)
        if status == 200 and res:
            return json.dumps({'id': res['id']}), 200
        elif status == 404:
            return json.dumps({'erro': 'nao encontrado'}), 404
        else:
            return json.dumps({'erro': 'erro ao remover'}), 500


@app.route('/similares')
def get_similares():
    # tratando request
    acordes_tag = request.args.get('acordes')
    id_musica_tag = request.args.get('id_unico_musica')
    sequencia_tag = request.args.get('sequencia')
    pagina_tag = request.args.get('pagina','1')

    # se não existir, filtra por todos.
    generos_tag = request.args.get('generos')
    generos_key = generos
    if generos_tag:
        generos_key = generos_tag.split(',')

    acordes = []
    if acordes_tag:
        acordes = acordes_tag.split(',')
    elif id_musica_tag:
        musica = musicas[id_musica_tag]
        acordes = musica.acordes
    elif sequencia_tag:
        acordes_stripped = sequencia_tag.replace(' ', '')
        acordes_concat = acordes_stripped.replace(',','')
        similares = []

        if acordes_concat in sequencias:
            id_seq = sequencias[acordes_concat]
            similares = get_pagina(get_similares_por_sequencia(id_seq, generos_key), pagina_tag)
            return json.dumps(similares)
        # check custom sequences
        # try to find by exact acordes_str form
        # normalized forms
        custom = get_custom_by_acordes(acordes_stripped) or get_custom_by_acordes(acordes_concat.replace(',', ','))
        # also try if user passed comma form
        if not custom and ',' in acordes_stripped:
            custom = get_custom_by_acordes(acordes_stripped)
        if custom:
            seq_tokens = custom['acordes'].split(',')
            collection = apply_filtro(musicas.values(), generos_key)
            similares_list = []
            for musica in collection:
                if sequencia_aparece_na_cifra(seq_tokens, musica.cifra):
                    similar = {
                        'id_unico_musica': musica.id_unico_musica,
                        'id_artista': musica.id_artista,
                        'id_musica': musica.id_musica,
                        'nome_artista': musica.nome_artista,
                        'nome_musica': musica.nome_musica,
                        'popularidade': musica.popularidade,
                        'acordes': musica.acordes,
                        'genero': musica.genero,
                        'url': musica.url,
                    }
                    similares_list.append(similar)
            similares = get_pagina(similares_list, pagina_tag)
            return json.dumps(similares)
        return json.dumps(similares)

    similares = get_similares(acordes, generos_key, id_musica_tag)

    return json.dumps(get_pagina(similares, pagina_tag))

def get_similares_por_sequencia(id_seq, generos_key):
    # filtra para melhor desempenho
    collection = apply_filtro(musicas.values(), generos_key)

    similares = []
    for musica in collection:
        if str(id_seq) in musica.seqs_famosas:
            similar = {
                'id_unico_musica' : musica.id_unico_musica,
                'id_artista' : musica.id_artista,
                'id_musica' : musica.id_musica,
                'nome_artista' : musica.nome_artista,
                'nome_musica' : musica.nome_musica,
                'popularidade' : musica.popularidade,
                'acordes' : musica.acordes,
                'genero' : musica.genero,
                'url' : musica.url,
            }
            similares.append(similar)

    return similares


def get_pagina(colecao, pagina_tag):
    sl = (int(pagina_tag) - 1)*TAM_PAGINA
    return colecao[sl:sl+TAM_PAGINA]

def get_similares(acordes, generos_key, id_musica = None):

    # filtra para melhor desempenho
    collection = apply_filtro(musicas.values(), generos_key)

    similares = []
    for musica in collection:

        if musica.id_unico_musica != id_musica:

            inter = set(acordes).intersection(set(musica.acordes))
            diff = set(musica.acordes) - set(acordes)

            # somente as que tiverem interseção e as que forem
            # dos generos solicitados.
            if len(inter) > 0:
                similar = {
                        'id_unico_musica' : musica.id_unico_musica,
                        'id_artista' : musica.id_artista,
                        'id_musica' : musica.id_musica,
                        'nome_artista' : musica.nome_artista,
                        'nome_musica' : musica.nome_musica,
                        'popularidade' : musica.popularidade,
                        'acordes' : musica.acordes,
                        'genero' : musica.genero,
                        'url' : musica.url,
                        'diferenca' : list(diff),
                        'intersecao' : list(inter)
                }

                similares.append(similar)

    # ordenados por menor diferença, maior interseção e maior popularidade.
    return sorted(similares, key=lambda x: (len(x['diferenca']), -len(x['intersecao'])))

## Filtra a coleção de músicas por gênero.
def apply_filtro(musicas, generos_key):
    # filtra para melhor desempenho
    collection = []
    for genero in generos_key:
        if genero in generos:
            collection += genero_musicas[genero]
    return collection

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == '__main__':
    app.run(debug=True)
