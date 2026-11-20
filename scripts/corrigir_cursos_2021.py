#!/usr/bin/env python3
"""Corrige metadados 2021 usando a ordem oficial verificada da página do INEP.

Não baixa PDFs, não muda caminhos, hashes, bytes nem status. Antes de escrever,
valida 30 blocos de prova/gabarito/padrão de resposta e faz cópias de segurança.
"""
from __future__ import annotations
import csv
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Sequência oficial: https://www.gov.br/inep/pt-br/areas-de-atuacao/
# avaliacao-e-exames-educacionais/enade/provas-e-gabaritos/2021
CURSOS_2021 = [
    'Artes Visuais (Licenciatura)',
    'Ciência da Computação (Bacharelado)',
    'Ciência da Computação (Licenciatura)',
    'Ciências Biológicas (Bacharelado)',
    'Ciências Biológicas (Licenciatura)',
    'Ciências Sociais (Bacharelado)',
    'Ciências Sociais (Licenciatura)',
    'Design (Bacharelado)',
    'Educação Física (Bacharelado)',
    'Educação Física (Licenciatura)',
    'Filosofia (Bacharelado)',
    'Filosofia (Licenciatura)',
    'Física (Licenciatura)',
    'Geografia (Bacharelado)',
    'Geografia (Licenciatura)',
    'História (Bacharelado)',
    'História (Licenciatura)',
    'Letras – Inglês (Licenciatura)',
    'Letras – Português (Licenciatura)',
    'Letras – Português e Espanhol (Licenciatura)',
    'Letras – Português e Inglês (Licenciatura)',
    'Matemática (Licenciatura)',
    'Música (Licenciatura)',
    'Pedagogia (Licenciatura)',
    'Química (Bacharelado)',
    'Química (Licenciatura)',
    'Sistemas de Informação (Bacharelado)',
    'Tecnologia em Análise e Desenvolvimento de Sistemas',
    'Tecnologia em Gestão e Tecnologia da Informação',
    'Tecnologia em Redes de Computadores',
]

CAMPOS = ['ano','curso','tipo','descricao','url','pagina_origem','arquivo','sha256','bytes','status','erro','obtido_em_utc']
TIPOS = ['prova', 'gabarito', 'padrao_resposta']

def validar_e_corrigir(linhas):
    selecionados = [r for r in linhas if str(r['ano']) == '2021']
    if len(CURSOS_2021) != 30 or len(selecionados) != 90:
        raise ValueError(f'Esperados 90 registros de 2021 (30 cursos × 3); encontrados {len(selecionados)}. Sem alteracoes.')
    if len({r['url'] for r in selecionados}) != 90:
        raise ValueError('URLs duplicadas em 2021. Sem alteracoes.')
    alteradas = 0
    for i, curso in enumerate(CURSOS_2021):
        trio = selecionados[3*i:3*i+3]
        tipos = [r['tipo'] for r in trio]
        if tipos != TIPOS:
            raise ValueError(f'Grupo {i+1} nao segue prova/gabarito/padrao: {tipos}. Sem alteracoes.')
        stems = [Path(urlparse(r['url']).path).stem.lower() for r in trio[:2]]
        normalizados = [re.sub(r'^2021_(?:pv|gb)_', '', s) for s in stems]
        if normalizados[0] != normalizados[1]:
            raise ValueError(f'Grupo {i+1}, prova e gabarito divergem: {stems}. Sem alteracoes.')
        # A ordem e a correspondência acima evitam deslocar cursos entre blocos.
        # Não modificar cursos pré-identificados com nome diferente: revisão manual.
        for row in trio:
            anterior = row['curso']
            if anterior not in ('nao_identificado', '', curso):
                raise ValueError(f'Curso existente diferente no grupo {i+1}: {anterior!r}. Sem alteracoes.')
            if anterior != curso:
                alteradas += 1
    # Só modifica depois de todas as validações, pois a lista contém os mesmos dicionários.
    for i, curso in enumerate(CURSOS_2021):
        for row in selecionados[3*i:3*i+3]:
            row['curso'] = curso
    return alteradas


def salvar_atomico(linhas, pasta: Path):
    agora = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    fontes = [pasta/'catalogo_enade.csv', pasta/'catalogo_enade.jsonl']
    for p in fontes:
        if p.exists():
            shutil.copy2(p, p.with_name(p.name+'.backup_'+agora))
    # Manter tipos originais do JSONL (ano e bytes podem ser inteiros),
    # atualizando somente o campo 'curso' na mesma URL.
    nomes_por_url = {r['url']: r['curso'] for r in linhas}
    if fontes[1].is_file():
        with fontes[1].open('r', encoding='utf-8-sig') as f:
            json_rows = [json.loads(ln) for ln in f if ln.strip()]
        if len(json_rows) != len(linhas) or {r['url'] for r in json_rows} != set(nomes_por_url):
            raise ValueError('CSV e JSONL nao possuem o mesmo conjunto de URLs. Sem gravar.')
        for row in json_rows:
            if str(row.get('ano')) == '2021':
                row['curso'] = nomes_por_url[row['url']]
    else:
        json_rows = linhas
    # Arquivos temporarios no mesmo disco; replace de cada arquivo de forma atomica.
    tmp_csv = pasta/'.catalogo_enade_corrigido.csv.tmp'
    tmp_jsonl = pasta/'.catalogo_enade_corrigido.jsonl.tmp'
    try:
        with tmp_csv.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction='ignore')
            w.writeheader(); w.writerows(linhas)
        with tmp_jsonl.open('w', encoding='utf-8') as f:
            for item in json_rows:
                f.write(json.dumps(item, ensure_ascii=False)+'\n')
        os.replace(tmp_csv, fontes[0])
        os.replace(tmp_jsonl, fontes[1])
    finally:
        tmp_csv.unlink(missing_ok=True)
        tmp_jsonl.unlink(missing_ok=True)


def main():
    pasta=Path('data/manifests')
    csvpath=pasta/'catalogo_enade.csv'
    if not csvpath.is_file():
        sys.exit(f'ERRO: manifesto nao encontrado: {csvpath}. Execute na raiz do projeto original.')
    with csvpath.open('r', encoding='utf-8-sig',newline='') as f:
        linhas=list(csv.DictReader(f))
    try:
        alteradas=validar_e_corrigir(linhas)
    except ValueError as exc:
        sys.exit(f'ABORTADO (nenhum arquivo alterado): {exc}')
    salvar_atomico(linhas,pasta)
    print(json.dumps({
        'status':'CORRIGIDO', 'registros_totais':len(linhas),
        'cursos_2021':len(CURSOS_2021), 'registros_2021':90,
        'registros_corrigidos':alteradas,
        'cursos_nao_identificados_restantes':sum(x['curso']=='nao_identificado' for x in linhas),
        'pdfs_e_hashes_preservados':True,
        'nota':'Mantidos os caminhos locais e os status dos downloads; backups criados nos manifestos.'
    }, ensure_ascii=False, indent=2))

if __name__=='__main__':
    main()
