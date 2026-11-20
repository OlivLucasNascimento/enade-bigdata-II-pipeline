"""Extrai rascunhos auditáveis das provas ENADE; não inventa gabarito ou semântica.

A extração de fórmulas, imagens e tabelas NÃO está resolvida automaticamente;
referências e pendências são registradas para revisão humana (RF04).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import urlparse

from enade_pipeline.gabaritos import parse_gabarito
from enade_pipeline.decodificacao_2017 import KNOWN_HASHES_2017, blocos_decodificados
from enade_pipeline.higienizacao import higienizar_questao, contar_marcas

import fitz  # PyMuPDF

# Ex.: "QUESTÃO DISCURSIVA 01", "QUESTÃO 01", "QUESTÃO D1".
QUESTAO = re.compile(r'^QUEST[ÃA]O\s+(?:(DISCURSIVA)\s+)?(D?\d{1,2})(?:\b|$)', re.I)
ALTERNATIVA = re.compile(
    r'^\s*(?:([ⒶⒷⒸⒹⒺⓐⓑⓒⓓⓔ])|\(?([A-E])\)\s*|([A-E])[\.:\)]\s*|([A-E])(?:\s{2,}|\s+(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ0-9])))(.+?)\s*$',
    re.U,
)
CIRC = dict(zip('ⒶⒷⒸⒹⒺⓐⓑⓒⓓⓔ', 'ABCDEABCDE'))
# Nas provas de 2017, o gabarito visual aparece como glifo separado,
# seguido de um espaco e texto iniciando por letra minuscula.
ALTERNATIVA_2017 = re.compile(r'^\s*([A-E])\s+(.+?)\s*$')
PERCEPCAO = re.compile(r'^QUESTION[ÁA]RIO\s+DE\s+PERCEP[ÇC][ÃA]O\s+DA\s+PROVA', re.I)
FG = re.compile(r'^FORMA[ÇC][ÃA]O\s+GERAL\s*$', re.I)
CE = re.compile(r'^(?:COMPONENTE|CONHECIMENTO)\s+ESPEC[ÍI]FICO(?:\s+DA\s+[ÁA]REA)?\s*$', re.I)
TIPO_PROVA = {'prova'}


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for buf in iter(lambda: f.read(1024 * 1024), b''):
            h.update(buf)
    return h.hexdigest()


def pdf_from_manifest(row: dict[str, Any], base: Path) -> Path:
    """Localiza PDF do manifesto em Windows/Linux sem permitir sair de data/.

    Os caminhos no CSV usam '/' mesmo no Windows. Usar str(Path(...))
    transforma '/' em '\\' no Windows e, portanto, não serve para
    validar um prefixo como 'data/'.
    """
    raw = row.get('arquivo')
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError('Caminho de PDF ausente no manifesto')
    raw = raw.strip()
    # Bloqueia caminhos Windows absolutos, UNC e com unidade (C:...).
    if PureWindowsPath(raw).drive or raw.startswith(('\\', '/')):
        raise ValueError(f'Caminho absoluto não permitido: {raw}')
    # Normaliza somente separadores, independentemente do sistema operacional.
    rel = PurePosixPath(raw.replace('\\', '/'))
    if (not rel.parts or rel.parts[0] != 'data' or '..' in rel.parts
            or rel.suffix.lower() != '.pdf'):
        raise ValueError(f'Caminho de PDF inválido no manifesto: {raw}')
    root = base.resolve()
    data_dir = (root / 'data').resolve()
    target = root.joinpath(*rel.parts).resolve()
    if not target.is_relative_to(data_dir):
        raise ValueError('PDF fora da pasta de dados')
    return target


def alternativas_do_texto(texto: str, *, modo_2017: bool = False) -> tuple[str, list[dict[str, str]], bool]:
    """Reconhece A...D/E em sequência; não transforma frases isoladas em alternativas."""
    lines = texto.splitlines()
    candidates: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines):
        m = ALTERNATIVA.match(line)
        if not m and modo_2017:
            alternativa_2017 = ALTERNATIVA_2017.match(line)
            if alternativa_2017:
                candidates.append((i, alternativa_2017.group(1), alternativa_2017.group(2).strip()))
                continue
        if m:
            letter = CIRC.get(m.group(1), m.group(1)) if m.group(1) else next((g for g in m.groups()[1:4] if g), None)
            if letter:
                candidates.append((i, letter.upper(), m.group(5).strip()))
    # Preferir sequência consecutiva A/B/C/D/[E] de índices ascendentes.
    accepted = None
    for idx, (first, ch, val) in enumerate(candidates):
        if ch != 'A':
            continue
        seq = [(first, ch, val)]
        expected = 'B'
        for nxt in candidates[idx + 1:]:
            if nxt[1] == expected:
                seq.append(nxt)
                expected = chr(ord(expected) + 1)
                if expected > 'E':
                    break
            elif len(seq) > 0 and nxt[1] == 'A':
                break
        if len(seq) >= 4:
            accepted = seq
            break
    if not accepted:
        return texto.strip(), [], False
    alt_items = []
    for n, (line_idx, letter, start) in enumerate(accepted):
        end = accepted[n + 1][0] if n + 1 < len(accepted) else len(lines)
        rest = [x.strip() for x in lines[line_idx + 1:end] if x.strip()]
        alt_items.append({'letra': letter, 'texto': ' '.join([start] + rest).strip()})
    return '\n'.join(lines[:accepted[0][0]]).strip(), alt_items, True


def text_blocks(page: fitz.Page, *, decodificar_2017: bool = False) -> tuple[list[str], bool]:
    """Ordena blocos pela posição vertical, descartando marcas editoriais.

    Os gráficos do ENADE criam dezenas de blocos em duas metades da folha;
    confundir isso com diagramação em colunas antepõe dados do gráfico ao
    enunciado. Usar a ordem física vertical reduz esse erro, mantendo um
    alerta quando houver realmente colunas justapostas.
    """
    w, h = page.rect.width, page.rect.height
    blocks = []
    fonte_blocos = blocos_decodificados(page) if decodificar_2017 else page.get_text('blocks')
    for b in fonte_blocos:
        if len(b) < 7 or b[6] != 0 or not str(b[4]).strip():
            continue
        x0, y0, x1, y1 = map(float, b[:4])
        content = str(b[4])
        # Marca de autenticidade tem blocos próprios, presentes no PDF
        # oficial, não são parte de uma questão.
        if re.match(r'(?i)^\s*VALIDIN(?:E|3)?P?', content):
            continue
        # Linhas de rodapé/códigos/barcode.
        if re.fullmatch(r'(?s)\s*\*?[rR]0?\d{6,10}\*?\s*', content):
            continue
        if y0 < h * .052 or y1 > h * .962:
            continue
        blocks.append((x0, y0, x1, y1, content))
    if decodificar_2017:
        # Nas provas 2017 há páginas com duas questões em colunas paralelas.
        # Ordenar somente por altura misturava Q15/Q16, Q24/Q25 etc.
        headings_left = [b for b in blocks if b[0] < w * .50 and b[2] < w * .54
                         and QUESTAO.match(b[4].strip())]
        headings_right = [b for b in blocks if b[0] >= w * .49
                          and QUESTAO.match(b[4].strip())]
        if headings_left and headings_right:
            blocks.sort(key=lambda b: (0 if b[2] <= w * .52 else
                                       1 if b[0] >= w * .49 else 2,
                                       b[1], b[0]))
        else:
            blocks.sort(key=lambda b: (b[1], b[0]))
    else:
        blocks.sort(key=lambda b: (b[1], b[0]))
    # Só marcar como duas colunas caso existam blocos textuais grandes em
    # faixas laterais com sobreposição vertical, sem gráficos de muitos nós.
    left = [b for b in blocks if b[2] <= w * .49 and len(b[4]) > 70]
    right = [b for b in blocks if b[0] >= w * .51 and len(b[4]) > 70]
    two_col = len(left) >= 2 and len(right) >= 2
    return [b[4] for b in blocks], two_col


def parse_pdf(path: Path, *, ano: int, curso: str, pdf_url: str, pdf_sha256: str, area: str | None = None) -> tuple[list[dict], list[dict]]:
    """Produz questões rastreáveis e alertas. PDF precisa existir localmente."""
    issues: list[dict] = []
    questions: list[dict] = []
    if urlparse(pdf_url).scheme not in ('http', 'https'):
        raise ValueError('URL de origem inválida')
    current: dict | None = None
    section = 'nao_identificado'
    stopped = False
    with fitz.open(path) as document:
        if document.needs_pass:
            raise ValueError('PDF protegido por senha')
        if document.page_count == 0:
            raise ValueError('PDF sem páginas')
        for ix, page in enumerate(document):
            num_page = ix + 1
            blocks, columns = text_blocks(page, decodificar_2017=(ano == 2017 and pdf_sha256 in KNOWN_HASHES_2017))
            text = '\n'.join(blocks)
            if not text.strip():
                issues.append({'pdf': str(path), 'pagina': num_page, 'problema': 'pagina_sem_texto_ocr_pendente'})
                continue
            # Páginas inteiras sem questão são comuns: capa, instruções etc.
            images = []
            for info in page.get_image_info():
                bbox = info.get('bbox', (0, 0, 0, 0))
                x0, y0, x1, y1 = bbox
                size = max(0, x1 - x0) * max(0, y1 - y0)
                if size > page.rect.width * page.rect.height * 0.012 and page.rect.height * .06 < y0 < page.rect.height * .94:
                    images.append({'tipo': 'imagem_pdf', 'pagina': num_page,
                                   'bbox': [round(float(v), 1) for v in bbox],
                                   'descricao': None, 'conversao': 'pendente_revisao',
                                   'associacao': 'pagina_nao_questao'})
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if current is not None and PERCEPCAO.search(line):
                    stopped = True
                    break
                if FG.fullmatch(line):
                    section = 'FG'
                    continue
                if CE.fullmatch(line):
                    section = 'CE'
                    continue
                found = QUESTAO.match(line)
                if found:
                    if current is not None:
                        questions.append(current)
                    explicit_disc = bool(found.group(1)) or found.group(2).upper().startswith('D')
                    numero = int(found.group(2).upper().lstrip('D'))
                    if numero < 1 or numero > 99:
                        current = None
                        continue
                    # Em 2023 a numeração objetiva de FG é 01-09 e CE 10-38;
                    # só inferir esse limite neste ano e registrar essa inferência.
                    formacao = section
                    base_inferencia = 'cabecalho_pdf' if section != 'nao_identificado' else 'nao_identificado'
                    if formacao == 'nao_identificado' and ano == 2023:
                        if explicit_disc and numero in (1, 2):
                            formacao = 'FG' if numero == 1 else 'CE'
                            base_inferencia = 'modelo_enade_2023_a_conferir'
                        elif not explicit_disc and 1 <= numero <= 38:
                            formacao = 'FG' if numero <= 9 else 'CE'
                            base_inferencia = 'modelo_enade_2023_a_conferir'
                    question_type = 'discursiva' if explicit_disc else 'objetiva'
                    key = f'enade|{ano}|{curso}|{pdf_sha256}|{question_type}|{numero}'
                    current = {'id': hashlib.sha256(key.encode('utf-8')).hexdigest(),
                               'ano': ano, 'area': area or curso, 'curso': curso,
                               'tipo_formacao': formacao, 'origem_tipo_formacao': base_inferencia,
                               'numero_questao': numero, 'tipo_questao': question_type,
                               'texto_base': None, 'enunciado': '', 'alternativas': [],
                               'gabarito': None, 'anulada': False,
                               'competencias': [], 'objetos_conhecimento': [],
                               'midias': [], 'pendente_revisao': True,
                               'alertas': ['gabarito_nao_vinculado', 'competencias_pendentes', 'objetos_conhecimento_pendentes', 'revisar_texto'],
                               'origem': {'pdf_url': pdf_url, 'pdf_sha256': pdf_sha256,
                                          'pagina_inicial': num_page, 'pagina_final': num_page},
                               '_linhas': []}
                    tail = line[found.end():].strip(' :-–—\t')
                    if tail:
                        current['_linhas'].append(tail)
                elif current is not None:
                    current['_linhas'].append(line)
                    current['origem']['pagina_final'] = num_page
                    if columns and 'layout_colunas_revisao' not in current['alertas']:
                        current['alertas'].append('layout_colunas_revisao')
                    if images:
                        for img in images:
                            if img not in current['midias']:
                                current['midias'].append(img)
                        if 'imagem_sem_conversao' not in current['alertas']:
                            current['alertas'].append('imagem_sem_conversao')
            if stopped:
                break
        if current is not None:
            questions.append(current)
    result: list[dict] = []
    seen_ids: set[str] = set()
    for q in questions:
        raw = '\n'.join(q.pop('_linhas'))
        body, opts, detected = alternativas_do_texto(raw, modo_2017=(ano == 2017 and pdf_sha256 in KNOWN_HASHES_2017))
        q['enunciado'] = body
        q['alternativas'] = opts
        if q['tipo_questao'] == 'objetiva' and not detected:
            q['alertas'].append('alternativas_nao_identificadas')
            if ano == 2017 and pdf_sha256 in KNOWN_HASHES_2017 and q['numero_questao'] == 9:
                q['alertas'].append('alternativas_exclusivamente_graficas_pdf_2017')
                q['midias'].append({'tipo': 'alternativas_graficas',
                                   'pagina': q['origem']['pagina_inicial'],
                                   'descricao': 'Cinco diagramas de arvore AVL identificados por A-E',
                                   'conversao': 'pendente_revisao',
                                   'associacao': 'questao'})
        if len(body) < 35:
            q['alertas'].append('enunciado_curto_ou_incompleto')
        if q['id'] in seen_ids:
            issues.append({'pdf': str(path), 'pagina': q['origem']['pagina_inicial'], 'problema': 'questao_repetida_no_pdf', 'id': q['id']})
            continue
        seen_ids.add(q['id'])
        result.append(q)
    if ano == 2017 and pdf_sha256 in KNOWN_HASHES_2017:
        for q in result:
            if 'texto_decodificado_fonte_pdf_2017_revisao_pendente' not in q['alertas']:
                q['alertas'].append('texto_decodificado_fonte_pdf_2017_revisao_pendente')
    if not result:
        issues.append({'pdf': str(path), 'pagina': 0, 'problema': 'nenhuma_questao_encontrada'})
    return result, issues


def carregar_manifesto(manifest: Path, base: Path, limite_provas: int = 2) -> list[dict]:
    with manifest.open('r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    valid = []
    ja_escolhidos = set()
    for row in rows:
        if row.get('tipo') not in TIPO_PROVA or row.get('status') not in ('baixado', 'existente'):
            continue
        try:
            path = pdf_from_manifest(row, base)
        except ValueError:
            continue
        if not path.is_file():
            continue
        # Preferir uma prova por curso/ano no piloto; as variantes
        # ampliada/ledor/superampliada não devem inflar o número de questões.
        chave = (row['ano'], row['curso'])
        if chave in ja_escolhidos:
            continue
        ja_escolhidos.add(chave)
        row['_caminho_resolvido'] = str(path)
        valid.append(row)
        if limite_provas and len(valid) >= limite_provas:
            break
    return valid


def extrair_manifesto(manifest: Path, base: Path, destino: Path, max_provas: int = 2) -> dict:
    started = time.monotonic()
    rows = carregar_manifesto(manifest, base, max_provas)
    with manifest.open('r', encoding='utf-8-sig', newline='') as f:
        manifest_rows = list(csv.DictReader(f))
    gabaritos = {}
    for g in manifest_rows:
        if g.get('tipo') != 'gabarito' or g.get('status') not in ('baixado', 'existente'):
            continue
        try:
            gpath = pdf_from_manifest(g, base)
        except ValueError:
            continue
        if gpath.is_file():
            gabaritos[(str(g['ano']), g['curso'])] = (g, gpath)
    if not rows:
        raise RuntimeError('Nenhuma prova disponível no manifesto (tipo=prova e arquivo existente).')
    destino.mkdir(parents=True, exist_ok=True)
    saida = destino / 'questoes.jsonl'
    pend = destino / 'pendencias.jsonl'
    issues: list[dict] = []
    all_questions: dict[str, dict] = {}
    attempted = 0
    for row in rows:
        path = Path(row['_caminho_resolvido'])
        attempted += 1
        actual_hash = digest_file(path)
        expected_hash = str(row.get('sha256', '')).lower().strip()
        if expected_hash and actual_hash != expected_hash:
            issues.append({'pdf': str(path), 'pagina': 0, 'problema': 'hash_nao_confere_manifesto'})
            continue
        try:
            question_list, warnings = parse_pdf(path, ano=int(row['ano']), curso=row['curso'],
                                                pdf_url=row['url'], pdf_sha256=actual_hash)
            issues.extend(warnings)
            ginfo = gabaritos.get((str(row['ano']), row['curso']))
            if ginfo:
                grow, gpath = ginfo
                gh = digest_file(gpath)
                if grow.get('sha256') and grow['sha256'].lower() != gh:
                    issues.append({'pdf': str(gpath), 'pagina': 0, 'problema': 'hash_gabarito_nao_confere'})
                else:
                    answers, problems = parse_gabarito(gpath)
                    issues.extend({'pdf':str(gpath), 'pagina':0, 'problema':msg} for msg in problems)
                    for q in question_list:
                        match = answers.get((q['tipo_questao'], q['numero_questao']))
                        if match:
                            val = match['valor']
                            if q['tipo_questao'] == 'objetiva' and val in 'ABCDE':
                                q['gabarito'] = val
                                q['alertas'] = [a for a in q['alertas'] if a != 'gabarito_nao_vinculado']
                            elif val == 'ANULADA':
                                q['anulada'] = True
                                q['alertas'] = [a for a in q['alertas'] if a != 'gabarito_nao_vinculado']
                            q['origem']['gabarito_pdf_url'] = grow['url']
                            q['origem']['gabarito_pdf_sha256'] = gh
                            q['origem']['gabarito_pagina'] = match['pagina']
            for q in question_list:
                all_questions[q['id']] = q
        except (RuntimeError, ValueError, fitz.FileDataError) as exc:
            issues.append({'pdf': str(path), 'pagina': 0, 'problema': f'{type(exc).__name__}: {exc}'})
    # O bruto fica preservado para comparação/auditoria; a versão limpa não é
    # considerada validada: todas as questões continuam pendentes de revisão.
    saida_bruta = destino / 'questoes_brutas.jsonl'
    auditoria_marcas = destino / 'auditoria_marcas.jsonl'
    registros_limpos = []
    registros_auditados = []
    with saida_bruta.open('w', encoding='utf-8') as f:
        for q in all_questions.values():
            f.write(json.dumps(q, ensure_ascii=False) + '\n')
            limpa, audit = higienizar_questao(q)
            registros_limpos.append(limpa)
            if audit:
                registros_auditados.append(audit)
    with saida.open('w', encoding='utf-8') as f:
        for q in registros_limpos:
            f.write(json.dumps(q, ensure_ascii=False) + '\n')
    with auditoria_marcas.open('w', encoding='utf-8') as f:
        for audit in registros_auditados:
            f.write(json.dumps(audit, ensure_ascii=False) + '\n')
    with pend.open('w', encoding='utf-8') as f:
        for problem in issues:
            f.write(json.dumps(problem, ensure_ascii=False) + '\n')
    duration = time.monotonic() - started
    return {'arquivos_processados': attempted, 'questoes_encontradas': len(all_questions),
            'pendencias_pdf': len(issues), 'segundos': round(duration, 2),
            'arquivos_por_segundo': round(attempted / duration, 3) if duration else 0,
            'saida': str(saida), 'pendencias': str(pend),
            'saida_bruta': str(saida_bruta), 'auditoria_marcas': str(auditoria_marcas),
            'questoes_com_marca': len(registros_auditados),
            'marcas_removidas': sum(item['marcas_removidas'] for item in registros_auditados),
            'marcas_residuais': sum(contar_marcas(q) for q in registros_limpos),
            'por_tipo': dict(Counter(q['tipo_questao'] for q in all_questions.values())),
            'status': 'rascunhos_higienizados_pendentes_validacao_humana'}
