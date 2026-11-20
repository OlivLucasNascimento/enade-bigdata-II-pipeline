#!/usr/bin/env python3
"""Resumo com denominadores corretos (2 discursivas sem alternativas)."""
from __future__ import annotations
import argparse
import csv
from pathlib import Path


def resumir(csvpath:Path)->dict:
    with csvpath.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    if len(rows)!=50 or len({x['id'] for x in rows})!=50:
        raise ValueError('São exigidos 50 registros de IDs distintos')
    objetivos=[x for x in rows if x.get('tipo')=='objetiva']
    discursos=[x for x in rows if x.get('tipo')=='discursiva']
    if len(objetivos)+len(discursos)!=len(rows):raise ValueError('Tipo de questão desconhecido')
    medidas={
        'enunciado':('enunciado_correto_1_ou_0',rows),
        'alternativas':('alternativas_corretas_1_ou_0',objetivos),
        'tipo':('tipo_correto_1_ou_0',rows),
    }
    saida={}
    for nome,(campo,amostra) in medidas.items():
        valores=[x.get(campo,'').strip() for x in amostra]
        if len(valores)==0 or any(v not in ('0','1') for v in valores):
            raise ValueError(f'Avaliação de {nome} incompleta')
        corretos=valores.count('1');total=len(valores)
        saida[nome]={'corretos':corretos,'avaliados':total,'percentual':round(100*corretos/total,2)}
    if any(x.get('alternativas_corretas_1_ou_0','').strip() for x in discursos):
        raise ValueError('Discursivas não devem ter avaliação de alternativas')
    saida['alternativas']['nao_aplicavel']=len(discursos)
    return saida


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,default=Path.cwd())
    args=p.parse_args()
    metrics=resumir(args.base/'evidencias/A3_revisao_manual.csv')
    for nome,v in metrics.items():
        n_a=v.get('nao_aplicavel',0)
        print(f'{nome}: {v["corretos"]}/{v["avaliados"]} = {v["percentual"]:.2f}%' + (f' | Não se aplica: {n_a} discursivas' if n_a else ''))
if __name__=='__main__':main()
