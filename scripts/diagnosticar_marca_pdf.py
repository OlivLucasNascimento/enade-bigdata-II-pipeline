#!/usr/bin/env python3
"""Conferência local: verifica se marcas já estão na camada textual dos PDFs."""
from pathlib import Path
import csv
import json
import sys
import fitz
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enade_pipeline.extracao import pdf_from_manifest
from enade_pipeline.higienizacao import MARCA_ENADE


def main():
    manifest = ROOT / 'data/manifests/catalogo_enade.csv'
    with manifest.open(encoding='utf-8-sig',newline='') as f:
        linhas = list(csv.DictReader(f))
    vistos = set()
    dados = []
    for row in linhas:
        if row.get('tipo') != 'prova' or row.get('status') not in ('baixado','existente'):
            continue
        chave = (row.get('ano'),row.get('curso'))
        if chave in vistos: continue
        try: path = pdf_from_manifest(row,ROOT)
        except ValueError: continue
        if not path.is_file(): continue
        vistos.add(chave)
        ocorrencias = 0
        paginas = []
        with fitz.open(path) as doc:
            for n,p in enumerate(doc, 1):
                count = len(MARCA_ENADE.findall(p.get_text()))
                if count:
                    ocorrencias += count
                    paginas.append(n)
        dados.append({'curso':row['curso'], 'ano':row['ano'], 'pdf':str(path),
                      'ocorrencias_na_camada_textual':ocorrencias,
                      'paginas_com_marca':paginas})
        if len(dados) >= 2: break
    destino = ROOT/'evidencias'/'A3_marca_na_fonte_pdf.json'
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(dados,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dados,indent=2,ensure_ascii=False))
    print('OBS: ausência dessa sequência na camada textual não comprova que ela não exista como elemento visual.')

if __name__ == '__main__':main()
