#!/usr/bin/env python3
"""Aceite HUMANO vinculado ao SHA-256 do CSV, somente depois da conferência real.

Não automatiza nem substitui a análise das 50 questões com os PDFs originais.
"""
from __future__ import annotations
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.reindexar_v2 import completo, indicativo_ia, sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=ROOT)
    parser.add_argument('--responsavel', required=True)
    args = parser.parse_args()
    csvfile = args.base / 'evidencias/A3_revisao_manual.csv'
    with csvfile.open(encoding='utf-8-sig', newline='') as f:
        dados = list(csv.DictReader(f))
    if len(dados) != 50 or any(not completo(r) for r in dados):
        raise SystemExit('RECUSADO: faltam avaliações completas em 50 questões (objetivas exigem alternativas).')
    if any(indicativo_ia(r) for r in dados):
        raise SystemExit('RECUSADO: há avaliações identificadas como IA; revise com o PDF e atualize as observações antes de confirmar.')
    if not args.responsavel.strip():
        raise SystemExit('RECUSADO: informe o responsável pela conferência visual')
    print('Este aceite declara que um ser humano comparou as 50 questões com os PDFs originais.')
    confirmation = input('Digite exatamente CONFIRMO APOS CONFERENCIA para registrar: ')
    if confirmation != 'CONFIRMO APOS CONFERENCIA':
        raise SystemExit('Operação cancelada; nenhum arquivo alterado.')
    registro = {
        'responsavel': args.responsavel.strip(),
        'confirmacao_comparacao_pdf': True,
        'quantidade_confirmada': 50,
        'sha256_csv': sha(csvfile),
        'registrado_em_utc': datetime.now(timezone.utc).isoformat(),
        'observacao': 'Confirmação declarada pelo responsável; IA não emite este aceite.',
    }
    output = args.base / 'evidencias/A3_aceite_revisao_humana.json'
    output.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Aceite registrado em', output)


if __name__ == '__main__':
    main()
