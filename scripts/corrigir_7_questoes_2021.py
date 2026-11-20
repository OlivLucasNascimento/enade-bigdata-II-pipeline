"""Recupera sete questões ENADE 2021 com enunciado vazio, sem inferir respostas.

Uso: py scripts/corrigir_7_questoes_2021.py [--origem CAMINHO]
Requer o diagnóstico local gerado previamente e os PDFs oficiais respectivos.
Cria backup do JSONL, valida SHA256 dos PDFs, altera SOMENTE os sete IDs conhecidos.
Não acessa Kafka/Elasticsearch nem faz commit/push.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_ORIGEM = PROJECT.parent / 'ENADE BigData II Projeto'
SOURCE_REL = Path('data/extraidos_2017_2021_corrigidos/questoes.jsonl')
DIAGNOSTIC = 'diagnostico_7_questoes_2021.zip'
EXPECTED_IDS = {
    '9d5eca53399cb2d077feb81476cc997f7368545173f40b8e098831f1b86db003',
    'ffd0dbd3dfe963ed37d3d8183e8da98e2b1136c1844d3bcaa6348fd88041dff7',
    '2afb7c094d6049638b322887d05abbc189ffa89d9a26de3c0877c3a2730a2889',
    '64c787cdf2a19837834682f8fd0d1ca1de248491b0e25eff347aa62d70664715',
    '2cc5aa43bd70ca61d978d86f14c058e1237b1ede3719060e7777cd6c64a452a4',
    '455d31a86f5f0f8097ef64d45d461d0b62efae3aa7c1d13cd4c2518137188118',
    'a72d5e84f3ebfea4ce5b336002bdf4f536cebda4445e22910b0948e80d127d88',
}
HEAD = re.compile(r'^\s*QUEST[ÃA]O\s+(\d{1,2})\s*$', re.IGNORECASE)
OPTION = re.compile(r'^\s*([A-E])(?:\t+| {2,})[ \t]*(\S.*)$')
STOP = re.compile(r'^\s*(?:[ÁA]rea livre|\*R\d{6,}\*|RASCUNHO)\s*$', re.IGNORECASE)
RECOVERY_ALERT = 'extracao_pdf_2021_duas_colunas_recuperada_revisao_pendente'


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def secao_da_questao(texto: str, numero: int) -> list[str]:
    """Corta seção da questão na ordem de leitura ORIGINAL do PDF, não por y."""
    lines = texto.splitlines()
    found = False
    section: list[str] = []
    for raw in lines:
        line = raw.strip()
        m = HEAD.fullmatch(line)
        if m:
            if found:
                break
            if int(m.group(1)) == numero:
                found = True
            continue
        if not found:
            continue
        if STOP.fullmatch(line):
            break
        if line:
            section.append(line)
    if not found:
        raise ValueError(f'Cabecalho da questao {numero} nao encontrado')
    if not section:
        raise ValueError(f'Secao vazia da questao {numero}')
    return section


def extrair_questao(texto: str, numero: int) -> tuple[str, list[dict]]:
    """Só aceita o conjunto completo de alternativas textuais A-E."""
    lines = secao_da_questao(texto, numero)
    starts: list[tuple[int, str, str]] = []
    for pos, raw in enumerate(lines):
        m = OPTION.fullmatch(raw)
        if m:
            starts.append((pos, m.group(1), m.group(2).strip()))
    letters = [letter for _, letter, _ in starts]
    if letters != list('ABCDE'):
        raise ValueError(f'Questao {numero}: alternativas incompletas ou ambiguas: {letters}')
    if starts[0][0] == 0:
        raise ValueError(f'Questao {numero}: enunciado sem texto')
    body = normalize('\n'.join(lines[:starts[0][0]]))
    if len(body) < 80:
        raise ValueError(f'Questao {numero}: enunciado muito curto ({len(body)})')
    opts = []
    for i, (start, letter, first) in enumerate(starts):
        limit = starts[i + 1][0] if i + 1 < len(starts) else len(lines)
        parts = [first] + lines[start + 1:limit]
        alt = normalize(' '.join(parts))
        if len(alt) < 2:
            raise ValueError(f'Questao {numero}: alternativa {letter} vazia')
        opts.append({'letra': letter, 'texto': alt})
    if len(set((item['letra'] for item in opts))) != 5:
        raise ValueError('Alternativas duplicadas')
    return body, opts


def read_jsonl(path: Path) -> list[dict]:
    values = []
    for n, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f'JSON invalido na linha {n}')
        values.append(value)
    return values


def diagnostic_text(zf: zipfile.ZipFile, rec: dict) -> str:
    page = rec['origem']['pagina_inicial']
    images = [str(x) for x in rec.get('imagens', []) if x.endswith(f'_pagina_{page}.png')]
    if len(images) != 1:
        raise ValueError('Pagina do diagnostico nao univoca para ' + rec['id'])
    entry = images[0]
    if not entry.startswith('paginas/') or '..' in entry.split('/'):
        raise ValueError('Caminho invalido no diagnostico')
    ref = 'textos/' + entry.split('/', 1)[1].removesuffix('.png') + '.txt'
    data = zf.read(ref).decode('utf-8-sig')
    first = '=== TEXTO SEM ORDENAR ==='
    second = '=== BLOCOS E COORDENADAS ==='
    if first not in data or second not in data:
        raise ValueError('Texto do PDF nao encontrado em ' + ref)
    return data.split(first, 1)[1].split(second, 1)[0].strip()


def localizar_pdf(origem: Path, rec: dict) -> Path:
    name = rec['pdf_original_nome']
    if Path(name).name != name or '/' in name or '\\' in name or not name.lower().endswith('.pdf'):
        raise ValueError('Nome do PDF inseguro no diagnostico')
    matches = list((origem / 'data').rglob(name))
    if len(matches) != 1:
        raise ValueError(f'Esperado um PDF original {name}; encontrados {len(matches)}')
    return matches[0]


def reparar(origem: Path, *, apenas_diagnostico: bool = False) -> dict:
    import fitz

    path = origem / SOURCE_REL
    zip_path = origem / DIAGNOSTIC
    if not path.is_file() or not zip_path.is_file():
        raise FileNotFoundError('Nao encontrado JSONL ou ZIP do diagnostico na pasta original')
    before_bytes = path.read_bytes()
    before_sha = hashlib.sha256(before_bytes).hexdigest()
    items = read_jsonl(path)
    if len(items) != 200:
        raise ValueError(f'Total inesperado na origem: {len(items)} (esperado 200)')
    ids = [q.get('id') for q in items]
    if len(set(ids)) != 200 or any(not q for q in ids):
        raise ValueError('IDs duplicados ou vazios na origem')
    by_id = {q['id']: q for q in items}
    if not EXPECTED_IDS <= set(by_id):
        raise ValueError('Faltam IDs esperados nas 200 questoes')
    was_blank = {q['id'] for q in items if not isinstance(q.get('enunciado'), str) or not q['enunciado'].strip()}
    if not (was_blank == EXPECTED_IDS or not was_blank):
        raise ValueError(f'Conjunto de enunciados vazios inesperado: {len(was_blank)}')

    corrected = copy.deepcopy(items)
    corrected_by_id = {q['id']: q for q in corrected}
    PDF_CACHE: dict[str, tuple[Path, str]] = {}
    results = []
    with zipfile.ZipFile(zip_path) as zf:
        refs = json.loads(zf.read('registros_com_lacunas.json').decode('utf-8-sig'))
        if len(refs) != 7 or {r['id'] for r in refs} != EXPECTED_IDS:
            raise ValueError('Diagnostico nao contem exatamente os sete IDs autorizados')
        for rec in refs:
            q = corrected_by_id[rec['id']]
            origin = q['origem']
            if q['ano'] != 2021 or q['numero_questao'] != rec['numero_questao'] or q['curso'] != rec['curso']:
                raise ValueError('Metadados inesperados para ' + rec['id'])
            if origin['pdf_sha256'] != rec['origem']['pdf_sha256'] or origin['pagina_inicial'] != rec['origem']['pagina_inicial']:
                raise ValueError('Origem do PDF divergente para ' + rec['id'])
            pdf = localizar_pdf(origem, rec)
            if str(pdf) not in PDF_CACHE:
                source_sha = digest(pdf)
                if source_sha != origin['pdf_sha256']:
                    raise ValueError('SHA256 do PDF NAO confere para ' + pdf.name)
                PDF_CACHE[str(pdf)] = (pdf, source_sha)
            snapshot = diagnostic_text(zf, rec)
            with fitz.open(pdf) as doc:
                page_index = origin['pagina_inicial'] - 1
                if page_index < 0 or page_index >= len(doc):
                    raise ValueError('Pagina fora do PDF: ' + rec['id'])
                current_text = doc[page_index].get_text('text', sort=False)
            # Conteudo trazido pelo diagnostico deve refletir o PDF validado (com SHA).
            if normalize(snapshot) != normalize(current_text):
                raise ValueError('Snapshot e texto PDF nao conferem para ' + rec['id'])
            body, opts = extrair_questao(current_text, q['numero_questao'])
            if was_blank:
                if q.get('enunciado') or q.get('alternativas'):
                    raise ValueError('Registro alvo com texto/alternativas inesperados')
                q['enunciado'] = body
                q['alternativas'] = opts
                q['alertas'] = [a for a in q.get('alertas', []) if a not in (
                    'alternativas_nao_identificadas', 'enunciado_curto_ou_incompleto')]
                if RECOVERY_ALERT not in q['alertas']:
                    q['alertas'].append(RECOVERY_ALERT)
                q['pendente_revisao'] = True
            else:
                # Em execucao repetida, confirmar exatamente o conteudo existente.
                if q.get('enunciado') != body or q.get('alternativas') != opts:
                    raise ValueError('Registro ja preenchido diverge do PDF; nao sobrescrever')
            results.append({'id': q['id'], 'curso': q['curso'], 'questao': q['numero_questao'],
                            'pagina': origin['pagina_inicial'], 'alternativas': len(opts),
                            'enunciado_caracteres': len(body), 'sha256_pdf': origin['pdf_sha256']})

    new_ids = [q['id'] for q in corrected]
    if new_ids != ids:
        raise ValueError('Ordem ou IDs alterados')
    expected_non_targets = [q for q in items if q['id'] not in EXPECTED_IDS]
    actual_non_targets = [q for q in corrected if q['id'] not in EXPECTED_IDS]
    if expected_non_targets != actual_non_targets:
        raise ValueError('Alteracoes indevidas em registros nao-alvo')
    if any(not q.get('enunciado', '').strip() for q in corrected):
        raise ValueError('Ainda existem enunciados vazios no lote')
    if Counter(q['ano'] for q in corrected) != {2017: 80, 2021: 120}:
        raise ValueError('Distribuicao de anos alterada')
    report = {'resultado': 'DIAGNOSTICO_OK' if apenas_diagnostico else 'CORRIGIDO_SEM_REVISAO_HUMANA',
              'registros': 200, 'ids_unicos': 200, 'alvos': 7,
              'enunciados_vazios_depois': 0, 'alterados': 7 if was_blank else 0,
              'idempotente': not bool(was_blank), 'sha256_anterior': before_sha,
              'pdfs_sha256_verificados': len(PDF_CACHE), 'detalhes': results,
              'revisao_humana': 'PENDENTE',
              'observacao': 'Recupera somente texto PDF e alternativas A-E, sem garantir revisao editorial ou semantica.'}
    if apenas_diagnostico:
        return report
    if was_blank:
        # Salvar backup imutavel nomeado pelo hash original, antes de sobrescrever.
        backup = path.with_name(f'questoes_antes_7_corr_2021_{before_sha[:16]}.jsonl')
        if backup.exists() and digest(backup) != before_sha:
            raise ValueError('Backup existente com conteudo diferente')
        if not backup.exists():
            with backup.open('xb') as output:
                output.write(before_bytes)
        if digest(backup) != before_sha:
            raise ValueError('Backup divergente')
        report['backup'] = str(backup)
        # Troca atomica do arquivo no mesmo volume.
        tmp_name = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                             prefix='.questoes_2021_', suffix='.tmp',
                                             dir=path.parent, delete=False) as temp:
                tmp_name = temp.name
                for q in corrected:
                    temp.write(json.dumps(q, ensure_ascii=False) + '\n')
            os.replace(tmp_name, path)
        finally:
            if tmp_name and os.path.exists(tmp_name):
                os.unlink(tmp_name)
    report['sha256_depois'] = digest(path)
    evidence = PROJECT / 'evidencias/A3_correcao_7_questoes_2021.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--origem', type=Path, default=DEFAULT_ORIGEM)
    p.add_argument('--diagnostico', action='store_true', help='Confere sem alterar arquivos')
    args = p.parse_args()
    try:
        result = reparar(args.origem.resolve(), apenas_diagnostico=args.diagnostico)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f'ERRO: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
