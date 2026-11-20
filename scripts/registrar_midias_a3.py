#!/usr/bin/env python3
"""Adiciona referências visuais auditáveis às questões com figuras.

Não altera questoes.jsonl. Cria questoes_com_midias.jsonl e renders PNG de
páginas do PDF oficial. Não aprova automaticamente nenhuma questão.
Requer PyMuPDF (import pymupdf) e Python >=3.10.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from collections import Counter
from pathlib import Path

import pymupdf

# Itens cujas figuras são essenciais ao enunciado ou às alternativas.
# Esta lista NÃO significa que as imagens tenham sido semanticamente convertidas.
GRAFICAS = {(2023, 'Arquitetura e Urbanismo', 11), (2023, 'Arquitetura e Urbanismo', 16)}
VISUAIS_PRIORITARIAS = {
    (2023, 'Agronomia', 3): 'grafico_vacinacao',
    (2023, 'Agronomia', 5): 'infografico_mobilidade',
    (2023, 'Agronomia', 26): 'tabela_a_conferir',
    (2023, 'Agronomia', 31): 'grafico_germinacao',
    (2023, 'Agronomia', 32): 'grafico_demanda_agua',
    (2023, 'Arquitetura e Urbanismo', 11): 'alternativas_vetoriais',
    (2023, 'Arquitetura e Urbanismo', 29): 'diagrama_acustica',
}

def remover_artefato_norte(q: dict) -> bool:
    """Remove um único símbolo N da rosa-dos-ventos, observado na Q11.

    Não altera o PDF, nem corrige textos não comprovados.
    """
    if ((q.get('ano'), q.get('curso'), q.get('numero_questao'))
        != (2023, 'Arquitetura e Urbanismo', 11)):
        return False
    texto = q.get('enunciado', '')
    if not isinstance(texto, str):
        return False
    texto_limpo, total = re.subn(
        r'^N[ \t\r\n]+(?=Considerando-se o desenho de uma planta de cobertura)', '', texto, count=1
    )
    if total != 1:
        return False
    q['enunciado'] = texto_limpo
    q.setdefault('alertas', []).append('artefato_norte_removido_conferir_pdf')
    return True


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def localizar_pdf(pasta: Path, curso: str, hash_esperado: str) -> Path:
    s = 'agronomia' if curso == 'Agronomia' else 'arquitetura-e-urbanismo'
    for p in sorted(pasta.rglob('*.pdf')):
        if s not in p.name.lower() or 'prova' not in p.name.lower():
            continue
        if sha256(p).lower() == hash_esperado.lower():
            return p
    raise FileNotFoundError(f'PDF original {curso}, SHA-256={hash_esperado} não encontrado em {pasta}')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', default='.', help='Raiz do projeto (contém data/raw e data/extraidos)')
    ap.add_argument('--dpi', type=int, default=150)
    opt = ap.parse_args()
    base = Path(opt.base).resolve()
    origem = base/'data'/'extraidos'/'questoes.jsonl'
    dados = [json.loads(line) for line in origem.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not dados or len({q['id'] for q in dados}) != len(dados):
        raise ValueError('JSONL ausente ou IDs duplicados: não foi gerada nenhuma saída')
    alteradas = []
    img_dir = base/'data'/'midias'/'a3_paginas'
    img_dir.mkdir(parents=True, exist_ok=True)
    fontes: dict[str, Path] = {}
    imagens = {}
    registros = []
    visuais_priori = []
    artefatos_corrigidos = []
    # Cada documento é reaberto somente na renderização necessária; PDFs nunca são alterados.
    for raw in dados:
        q = deepcopy(raw)
        if remover_artefato_norte(q):
            artefatos_corrigidos.append(q['id'])
        tipo = q.get('tipo_questao')
        chave = (q.get('ano'), q.get('curso'), q.get('numero_questao'))
        precisa = bool(q.get('midias')) or chave in GRAFICAS or chave in VISUAIS_PRIORITARIAS
        if not precisa:
            registros.append(q)
            continue
        pdfhash = q['origem']['pdf_sha256']
        if pdfhash not in fontes:
            fontes[pdfhash] = localizar_pdf(base/'data'/'raw', q['curso'], pdfhash)
        source = fontes[pdfhash]
        inicio = int(q['origem']['pagina_inicial'])
        fim = int(q['origem']['pagina_final'])
        complemento = []
        with pymupdf.open(source) as doc:
            if inicio < 1 or fim > doc.page_count or fim < inicio:
                raise ValueError(f'Páginas incoerentes no registro {q["id"]}')
            for pagina in range(inicio, fim + 1):
                tag = f'{pdfhash[:12]}_p{pagina:02d}'
                arquivo_relativo = f'data/midias/a3_paginas/{tag}.png'
                destino = base/arquivo_relativo
                if tag not in imagens:
                    px = doc[pagina-1].get_pixmap(dpi=opt.dpi, alpha=False)
                    px.save(destino)
                    imagens[tag] = {'arquivo': arquivo_relativo, 'pagina': pagina,
                                    'sha256': sha256(destino), 'fonte_pdf_sha256': pdfhash}
                complemento.append({
                    'tipo': 'pagina_pdf_renderizada',
                    'pagina': pagina,
                    'arquivo': arquivo_relativo,
                    'descricao': 'Página oficial da prova para conferência visual, incluindo figuras e alternativas gráficas',
                    'conversao': 'referencia_visual_sem_transcricao_automatica',
                    'associacao': 'intervalo_paginas_questao',
                    'pdf_sha256': pdfhash,
                    'imagem_sha256': imagens[tag]['sha256'],
                })
        # Não remove mídias da extração original nem inventa texto de alternativas.
        q['midias'] = list(q.get('midias') or []) + complemento
        avisos = list(q.get('alertas') or [])
        if 'figuras_para_conferencia_visual' not in avisos:
            avisos.append('figuras_para_conferencia_visual')
        if chave in VISUAIS_PRIORITARIAS:
            visuais_priori.append(q['id'])
            aviso = 'midia_essencial_pendente_semantica:' + VISUAIS_PRIORITARIAS[chave]
            if aviso not in avisos: avisos.append(aviso)
        if chave in GRAFICAS and 'alternativas_graficas_nao_transcritas' not in avisos:
            avisos.append('alternativas_graficas_nao_transcritas')
        q['alertas'] = avisos
        q['pendente_revisao'] = True
        alteradas.append(q['id'])
        registros.append(q)

    saida = base/'data'/'extraidos'/'questoes_com_midias.jsonl'
    with saida.open('w', encoding='utf-8', newline='\n') as f:
        for q in registros:
            f.write(json.dumps(q, ensure_ascii=False) + '\n')
    resumo = {
        'total_questoes': len(registros),
        'ids_preservados': [r['id'] for r in registros] == [r['id'] for r in dados],
        'questoes_com_referencia_visual_adicionada': len(alteradas),
        'arquivos_png_gerados': len(imagens),
        'alternativas_graficas_sem_transcricao': 2,
        'questoes_visuais_prioritarias_com_referencia': len(visuais_priori),
        'artefatos_norte_removidos_em_versao_derivada': len(artefatos_corrigidos),
        'aviso_qualidade': 'Referência em PNG não equivale a transcrição semântica; revise gráficos, tabelas e diagramas.',
        'aprovacao_editorial': 'PENDENTE',
        'jsonl_original_preservado': str(origem.relative_to(base)),
        'jsonl_derivado': str(saida.relative_to(base)),
        'imagens': list(imagens.values()),
        'nota': 'Renders preservam figuras vetoriais. Não comprovam extração semântica ou correção de gabarito.'
    }
    if not resumo['ids_preservados'] or len(registros)!=len(dados):
        raise AssertionError('Invariantes de IDs/contagem violados')
    evid = base/'evidencias'
    evid.mkdir(exist_ok=True)
    (evid/'A3_paginas_visuais_resumo.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in resumo.items() if k!='imagens'}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
