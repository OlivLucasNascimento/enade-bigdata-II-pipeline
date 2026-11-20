#!/usr/bin/env python3
"""Consolida a auditoria humana A3 (50 PDFs) sem alterar evidências originais.

Opcionalmente gera um JSONL derivado corrigindo APENAS rascunhos numerados
em enunciados de discursivas reprovados pela auditoria. Não edita a fonte,
não reclassifica aprovações e não reindexa Elasticsearch.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone

COLS = ('enunciado_correto_1_ou_0', 'alternativas_corretas_1_ou_0', 'tipo_correto_1_ou_0')
RASCUNHO = re.compile(r'(?m)^\s*RASCUNHO\s*\r?\n((?:[ \t]*\d{1,2}[ \t]*(?:\r?\n|$)){5,})\s*\Z',re.I)


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def limpar_rascunho(texto:str)->str | None:
    """Somente remove bloco RASCUNHO final, numerado 1..N consecutivamente."""
    if not isinstance(texto,str):return None
    m=RASCUNHO.search(texto)
    if not m:return None
    numeros=[int(n) for n in re.findall(r'(?m)^\s*(\d{1,2})\s*$',m.group(1))]
    if len(numeros)<5 or numeros != list(range(1,len(numeros)+1)):
        return None
    return texto[:m.start()].rstrip()


def processar(base:Path, aplicar:bool=False)->dict:
    csvpath=base/'evidencias/A3_revisao_manual.csv'
    jsonl=base/'data/extraidos/questoes_com_midias.jsonl'
    if not jsonl.exists(): jsonl=base/'data/extraidos/questoes.jsonl'
    if not csvpath.is_file() or not jsonl.is_file():
        raise FileNotFoundError('CSV de auditoria ou JSONL de 2023 não encontrado na pasta original')
    with csvpath.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    if len(rows)!=50 or len({x['id'] for x in rows})!=50:
        raise ValueError('Auditoria não contém 50 IDs distintos')
    if any(x['tipo_correto_1_ou_0'].strip() not in ('0','1') or x['enunciado_correto_1_ou_0'].strip() not in ('0','1') for x in rows):
        raise ValueError('Há campos de enunciado ou tipo pendentes')
    for x in rows:
        val=x['alternativas_corretas_1_ou_0'].strip()
        if x['tipo']=='objetiva' and val not in ('0','1'):
            raise ValueError(f'Alternativas objetivas pendentes: {x["id"][:12]}')
        if x['tipo']=='discursiva' and val:
            raise ValueError(f'Alternativas discursivas não devem ser avaliadas: {x["id"][:12]}')
    dados=[json.loads(s) for s in jsonl.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    if len(dados)!=80 or len({x['id'] for x in dados})!=80:
        raise ValueError('Lote de 2023 precisa ter 80 IDs únicos')
    porid={x['id']:x for x in dados}
    if any(x['id'] not in porid for x in rows):
        raise ValueError('Auditoria tem IDs ausentes do JSONL original')
    if any(x['tipo']!=porid[x['id']].get('tipo_questao') for x in rows):
        raise ValueError('Tipo no CSV difere do tipo do JSONL')
    objs=[x for x in rows if x['tipo']=='objetiva']
    dis=[x for x in rows if x['tipo']=='discursiva']
    erros=[x for x in rows if x['enunciado_correto_1_ou_0']=='0']
    rascunhos=[x for x in erros if x['tipo']=='discursiva' and 'RASCUNHO' in x.get('observacoes','').upper()]
    visuais=[x for x in erros if x not in rascunhos]
    metricas={
        'enunciado':{'aprovados':sum(x[COLS[0]]=='1' for x in rows),'avaliados':len(rows)},
        'alternativas':{'aprovados':sum(x[COLS[1]]=='1' for x in objs),'avaliados':len(objs),'nao_aplicavel':len(dis)},
        'tipo':{'aprovados':sum(x[COLS[2]]=='1' for x in rows),'avaliados':len(rows)},
    }
    problemas=[]
    for x in erros:
        q=porid[x['id']]
        problemas.append({'id':x['id'],'ano':x['ano'],'curso':x['curso'],'numero_questao':q.get('numero_questao'),
                          'pagina':x['pagina'],'categoria':'ruido_rascunho' if x in rascunhos else 'visual_ou_outro',
                          'observacoes':x.get('observacoes','')})
    resultado={'status':'AUDITORIA_HUMANA_REGISTRADA_PENDENCIAS',
        'total_avaliados':len(rows),'ids_unicos':len({x['id'] for x in rows}),
        'fonte_csv':str(csvpath.relative_to(base)),'sha256_csv':sha(csvpath),
        'fonte_jsonl':str(jsonl.relative_to(base)),'sha256_jsonl':sha(jsonl),
        'metricas':metricas,'problemas_total':len(problemas),
        'rascunhos_identificados':len(rascunhos),'visuais_ou_outros_identificados':len(visuais),
        'problemas':problemas,
        'observacoes':['Avaliação humana da amostra de 2023: não valida os 280 registros completos.',
        'Alternativas de questões discursivas são não aplicáveis, não pendentes.',
        'Referência a PNG de página não comprova conversão semântica do elemento visual.',
        'Nota de auditoria original é imutável; correções exigem nova avaliação.']}
    if aplicar:
        novos=deepcopy(dados)
        ids_rasc={x['id'] for x in rascunhos}
        corrigidos=[];nao_corrigidos=[]
        for q in novos:
            if q['id'] not in ids_rasc:continue
            editado=limpar_rascunho(q.get('enunciado',''))
            if editado is None:
                nao_corrigidos.append(q['id']);continue
            q['enunciado']=editado
            q.setdefault('alertas',[]).append('rascunho_removido_em_derivado_pendente_revisao')
            q['pendente_revisao']=True
            corrigidos.append(q['id'])
        if nao_corrigidos:
            raise ValueError('Rascunho com formato inesperado; NENHUM dado escrito: '+','.join(x[:12] for x in nao_corrigidos))
        if len(corrigidos)!=len(ids_rasc):raise AssertionError('Quantidade de rascunhos não confere')
        if [x['id'] for x in novos] != [x['id'] for x in dados]:
            raise AssertionError('IDs não preservados')
        for q in novos:
            original=porid[q['id']]
            if q['id'] not in ids_rasc and q != original:raise AssertionError('Registro não alvo alterado')
        dest=base/'data/extraidos_auditados_2023/questoes.jsonl'
        dest.parent.mkdir(parents=True,exist_ok=True)
        tmp=dest.with_suffix('.jsonl.tmp')
        tmp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in novos),encoding='utf-8')
        tmp.replace(dest)
        resultado['derivado_criado']=str(dest.relative_to(base))
        resultado['sha256_derivado']=sha(dest)
        resultado['rascunhos_corrigidos_no_derivado']=len(corrigidos)
        resultado['aviso_derivado']='Rascunhos limpos em versão separada; 8 pendências visuais permanecem. Não reindexado.'
    saida=base/'evidencias/A3_relatorio_auditoria_50.json'
    saida.parent.mkdir(parents=True,exist_ok=True)
    saida.write_text(json.dumps(resultado,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for titulo,item in metricas.items():
        print(f'{titulo}: {item["aprovados"]}/{item["avaliados"]} ({item["aprovados"]/item["avaliados"]*100:.1f}%)'+(f', não aplicável: {item["nao_aplicavel"]}' if 'nao_aplicavel' in item else ''))
    print(f'Problemas: {len(problemas)} | Rascunhos: {len(rascunhos)} | Visuais/outros: {len(visuais)}')
    print('Relatório:',saida)
    if aplicar:print('JSONL derivado:',dest,'| rascunhos corrigidos:',len(corrigidos))
    return resultado


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,default=Path.cwd())
    p.add_argument('--corrigir-rascunhos',action='store_true',help='Gera JSONL derivado; não altera originais.')
    a=p.parse_args();processar(a.base.resolve(),a.corrigir_rascunhos)
if __name__=='__main__':main()
