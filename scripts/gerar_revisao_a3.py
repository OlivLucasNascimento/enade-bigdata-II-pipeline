#!/usr/bin/env python3
"""Prepara planilha CSV de revisão manual aleatória (RNF03): sem inventar acertos."""
from __future__ import annotations
import argparse
import csv
import json
import random
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--entrada', type=Path, default=Path('data/extraidos/questoes.jsonl'))
    p.add_argument('--saida', type=Path, default=Path('evidencias/A3_revisao_manual.csv'))
    p.add_argument('--amostra', type=int, default=50)
    a = p.parse_args()
    qs = [json.loads(line) for line in a.entrada.read_text(encoding='utf-8').splitlines() if line.strip()]
    random.Random(2023).shuffle(qs)
    choice = qs[:a.amostra]
    a.saida.parent.mkdir(parents=True, exist_ok=True)
    with a.saida.open('w', newline='', encoding='utf-8-sig') as f:
        cols = ['id','curso','ano','pagina','tipo','previa','enunciado_correto_1_ou_0',
                'alternativas_corretas_1_ou_0','tipo_correto_1_ou_0','observacoes']
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for q in choice:
            writer.writerow({'id':q['id'], 'curso':q['curso'], 'ano':q['ano'],
                'pagina': q['origem']['pagina_inicial'], 'tipo':q['tipo_questao'],
                'previa':q['enunciado'][:180]})
    print(f'Amostra preparada: {len(choice)} / {len(qs)} questões em {a.saida}')
    if len(choice) < 50:
        print('ATENÇÃO: RNF03 exige avaliar manualmente pelo menos 50 questões; amplie as provas.')
    print('Preencha as colunas *_1_ou_0 somente após conferência com os PDFs.')


if __name__ == '__main__':
    main()
