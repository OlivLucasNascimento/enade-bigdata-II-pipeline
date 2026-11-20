#!/usr/bin/env python3
"""Representa as 10 alternativas gráficas (2 questões) com recortes do PDF oficial.

Nunca inventa texto, gabarito ou aprovação editorial. A imagem é a própria alternativa.
Entrada/saída: data/extraidos/questoes_com_midias.jsonl (derived, nunca o original).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import pymupdf

# Coordenadas em pontos do PDF ENADE 2023, aferidas nas páginas oficiais.
# As áreas incluem o símbolo A-E e o desenho correspondente.
RECORTES = {
    ('Arquitetura e Urbanismo', 11): {
        'pagina': 15,
        'retangulos': {
            'A': (24, 393, 340, 458),
            'B': (24, 459, 340, 533),
            'C': (24, 534, 340, 606),
            'D': (24, 607, 340, 675),
            'E': (24, 676, 340, 737),
        },
    },
    ('Arquitetura e Urbanismo', 16): {
        'pagina': 21,
        'retangulos': {
            'A': (24, 118, 250, 306),
            'B': (24, 318, 250, 540),
            'C': (24, 548, 250, 735),
            'D': (260, 118, 532, 305),
            'E': (260, 317, 532, 540),
        },
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def localizar_pdf(base: Path, curso: str, hash_pdf: str) -> Path:
    prefixo = 'arquitetura-e-urbanismo' if curso == 'Arquitetura e Urbanismo' else 'agronomia'
    for pdf in sorted((base / 'data' / 'raw').rglob('*.pdf')):
        if prefixo in pdf.name.lower() and 'prova' in pdf.name.lower() and sha256(pdf) == hash_pdf:
            return pdf
    raise FileNotFoundError('PDF fonte com SHA-256 exato nao encontrado em data/raw: ' + hash_pdf)


def completar(q: dict, *, base: Path, pdf_path: Path) -> tuple[dict, int]:
    chave = (q.get('curso'), q.get('numero_questao'))
    if (q.get('ano') != 2023 or q.get('tipo_questao') != 'objetiva' or
            chave not in RECORTES):
        return q, 0
    if len(q.get('alternativas', [])) not in (0, 5):
        raise ValueError(f'Alternativas inesperadas em {chave}; nao sobrescrevendo')
    if len(q.get('alternativas', [])) == 5 and not all(
            alt.get('tipo_representacao') == 'imagem_pdf' for alt in q['alternativas']):
        raise ValueError(f'Alternativas ja transcritas em {chave}; nao sobrescrevendo')
    esperado = q['origem']['pdf_sha256']
    if sha256(pdf_path) != esperado:
        raise ValueError(f'Hash do PDF nao coincide com a questao {chave}')
    configuracao = RECORTES[chave]
    pagina = configuracao['pagina']
    if not (q['origem']['pagina_inicial'] <= pagina <= q['origem']['pagina_final']):
        raise ValueError(f'Pagina {pagina} nao pertence a questao {chave}')
    dir_saida = base / 'data' / 'midias' / 'alternativas_graficas'
    dir_saida.mkdir(parents=True, exist_ok=True)
    alternativas, midias = [], []
    with pymupdf.open(pdf_path) as pdf:
        folha = pdf[pagina - 1]
        for letra, coords in configuracao['retangulos'].items():
            ret = pymupdf.Rect(coords)
            if not folha.rect.contains(ret):
                raise ValueError(f'Recorte fora da pagina: {chave}, alternativa {letra}')
            nome = f'{esperado[:12]}_q{chave[1]:02d}_{letra}.png'
            relativo = f'data/midias/alternativas_graficas/{nome}'
            destino = base / relativo
            folha.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=ret, alpha=False).save(destino)
            midias.append({
                'tipo': 'alternativa_grafica_png', 'letra': letra,
                'arquivo': relativo, 'pagina': pagina,
                'bbox_pdf': list(coords), 'imagem_sha256': sha256(destino),
                'pdf_sha256': esperado, 'conversao': 'recorte_fiel_sem_transcricao_semantica',
                'descricao': f'Alternativa {letra} na questao {chave[1]}: imagem fiel do PDF oficial',
            })
            alternativas.append({
                'letra': letra, 'texto': f'[Alternativa {letra} exclusivamente grafica; consultar imagem do PDF]',
                'tipo_representacao': 'imagem_pdf', 'imagem': relativo,
            })
    q['alternativas'] = alternativas
    # Substituir SOMENTE recortes que este programa gerou, para manter idempotencia.
    q['midias'] = [m for m in q.get('midias', []) if m.get('tipo') != 'alternativa_grafica_png'] + midias
    q['alertas'] = list(dict.fromkeys(list(q.get('alertas', [])) + [
        'alternativas_graficas_com_imagem_sem_transcricao_semantica',
        'alternativas_graficas_exigem_validacao_humana',
    ]))
    q['pendente_revisao'] = True
    return q, len(midias)


def executar(base: Path) -> dict:
    arquivo = base / 'data' / 'extraidos' / 'questoes_com_midias.jsonl'
    if not arquivo.is_file():
        raise FileNotFoundError('Execute registrar_midias_a3.py antes deste programa')
    qs = [json.loads(line) for line in arquivo.read_text(encoding='utf-8').splitlines() if line.strip()]
    anteriores = [q['id'] for q in qs]
    if len(anteriores) != len(set(anteriores)):
        raise ValueError('IDs repetidos no JSONL; nada sera salvo')
    fonte = {}
    total_recortes, tratados = 0, []
    for q in qs:
        chave = (q.get('curso'), q.get('numero_questao'))
        if q.get('ano') != 2023 or chave not in RECORTES or q.get('tipo_questao') != 'objetiva':
            continue
        pdf_hash = q['origem']['pdf_sha256']
        if pdf_hash not in fonte:
            fonte[pdf_hash] = localizar_pdf(base, q['curso'], pdf_hash)
        _, count = completar(q, base=base, pdf_path=fonte[pdf_hash])
        total_recortes += count
        tratados.append({'id': q['id'], 'curso': q['curso'], 'questao': q['numero_questao'], 'alternativas': count})
    if len(tratados) != 2 or total_recortes != 10 or [q['id'] for q in qs] != anteriores:
        raise ValueError(f'Esperadas 2 questoes/10 recortes; encontrados {len(tratados)}/{total_recortes}')
    conteudo = ''.join(json.dumps(q, ensure_ascii=False) + '\n' for q in qs)
    temporario = arquivo.with_suffix('.jsonl.tmp')
    temporario.write_text(conteudo, encoding='utf-8')
    os.replace(temporario, arquivo)
    resumo = {
        'status': 'IMAGENS_DAS_ALTERNATIVAS_ASSOCIADAS_SEM_APROVACAO_SEMANTICA',
        'questoes': tratados, 'recortes_png': total_recortes, 'ids_preservados': True,
        'revisao_humana': 'PENDENTE', 'gabaritos_inferidos': 0,
        'aviso': 'Recortes preservam os desenhos do PDF, nao interpretam seu significado.'
    }
    evid = base / 'evidencias'
    evid.mkdir(exist_ok=True)
    (evid / 'A3_alternativas_graficas_recortadas.json').write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    return resumo


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(executar(args.base.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
