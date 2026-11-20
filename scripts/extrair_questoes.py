#!/usr/bin/env python3
"""Etapa A3: extrai questões de provas reais já coletadas (manifesto A2)."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enade_pipeline.extracao import extrair_manifesto


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--manifesto', type=Path, default=ROOT / 'data/manifests/catalogo_enade.csv')
    p.add_argument('--saida', type=Path, default=ROOT / 'data/extraidos')
    p.add_argument('--limite-provas', type=int, default=2, help='0 para todas as provas locais do manifesto')
    args = p.parse_args(argv)
    if args.limite_provas < 0:
        p.error('limite-provas não pode ser negativo')
    resumo = extrair_manifesto(args.manifesto, ROOT, args.saida, args.limite_provas)
    caminho = ROOT / 'evidencias' / 'A3_resumo.json'
    caminho.parent.mkdir(exist_ok=True)
    caminho.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    if not resumo['questoes_encontradas']:
        print('ATENÇÃO: nenhuma questão detectada; inspeção de PDF necessária.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
