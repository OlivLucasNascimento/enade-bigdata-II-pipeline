#!/usr/bin/env python3
"""Calcula taxas SOMENTE a partir de auditoria humana efetivamente preenchida."""
import csv
from pathlib import Path

FILE = Path('evidencias/A3_revisao_manual.csv')
with FILE.open(encoding='utf-8-sig', newline='') as f:
    items = list(csv.DictReader(f))
columns = ['enunciado_correto_1_ou_0','alternativas_corretas_1_ou_0','tipo_correto_1_ou_0']
for col in columns:
    reviewed = [int(row[col]) for row in items if row.get(col,'').strip() in ('0', '1')]
    if len(reviewed) < 50:
        print(f'{col}: INSUFICIENTE — {len(reviewed)} revisões (mínimo 50).')
    else:
        print(f'{col}: {sum(reviewed)}/{len(reviewed)} = {sum(reviewed)/len(reviewed)*100:.2f}%')
