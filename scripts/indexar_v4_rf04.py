#!/usr/bin/env python3
"""Indexacao ENADE v4 por copia (sem escrita em v1/v2/v3 e sem alterar dados locais).

Fonte: 80 questoes de 2023 derivadas com 2 rascunhos limpos e 8 semanticas
       + 200 questoes de 2017/2021. Metadados de aceite APENAS do RF04.
Acoes: registrar-aprovacao, preflight, executar, verificar.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid
import csv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import indexar_v3 as v3
from scripts import estruturar_semantica_rf04 as sem4
from scripts.consolidar_auditoria_a3 import limpar_rascunho

INDICE = "enade-questoes-v4"
TOPICO = "enade.questoes.v4"
TOPICO_DLQ = "enade.questoes.v4.dlq"
ANTERIORES = ("enade-questoes-v1", "enade-questoes-v2", "enade-questoes-v3")
FONTE_2023 = Path("data/extraidos_auditados_2023/questoes_semantica_rf04.jsonl")
FONTE_2023_CLEAN = Path("data/extraidos_auditados_2023/questoes.jsonl")
ORIGINAL_2023 = Path("data/extraidos/questoes_com_midias.jsonl")
FONTE_ANTIGA = Path("data/extraidos_2017_2021_corrigidos/questoes.jsonl")
CSV = Path("evidencias/A3_revisao_manual.csv")
APROVACAO = ROOT / "evidencias/A3_rf04_aprovacao_editorial_8.json"
PREFLIGHT = ROOT / "evidencias/A4_v4_preflight.json"
VERIFICACAO = ROOT / "evidencias/A4_v4_verificacao.json"
DATA_V4 = Path("data/extraidos_280_v4/questoes.jsonl")
FRASE = "8 questões conferidas e aprovadas"


def agora():
    return datetime.now(timezone.utc).isoformat()


def salvar(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_canon(q: dict) -> str:
    return v3.digest_json(q)


def ler(path: Path, count: int, label: str) -> list[dict]:
    data = v3.read_jsonl(path)
    if len(data) != count:
        raise ValueError(f"{label}: esperado {count}, encontrado {len(data)}")
    ids = [q.get("id") for q in data]
    if len(set(ids)) != count or any(not isinstance(i, str) for i in ids):
        raise ValueError(f"{label}: IDs ausentes ou duplicados")
    return data


def csv_auditado(path: Path):
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 50 or len({r.get('id') for r in rows}) != 50:
        raise ValueError("Auditoria humana precisa conter 50 IDs unicos")
    for r in rows:
        if r.get('enunciado_correto_1_ou_0') not in ('0','1') or r.get('tipo_correto_1_ou_0') not in ('0','1'):
            raise ValueError("Auditoria humana com notas pendentes")
    return rows


def preparar_fontes(base: Path):
    """Verificacao estrita e SEM escrita: fonte inicial e 280 IDs esperados."""
    base = base.resolve()
    original = ler(base / ORIGINAL_2023, 80, "2023 original")
    clean = ler(base / FONTE_2023_CLEAN, 80, "2023 rascunhos corrigidos")
    sem = ler(base / FONTE_2023, 80, "2023 semantica RF04")
    antiga = ler(base / FONTE_ANTIGA, 200, "2017/2021")
    csvfile = base / CSV
    notas = csv_auditado(csvfile)
    notes = {n['id']: n for n in notas}
    o_by = {q['id']: q for q in original}
    c_by = {q['id']: q for q in clean}
    s_by = {q['id']: q for q in sem}
    if set(o_by) != set(c_by) or set(o_by) != set(s_by):
        raise ValueError("Os IDs de 2023 nao foram preservados")
    if not set(notes).issubset(o_by):
        raise ValueError("Auditoria humana contem ID desconhecido")
    if Counter(n['enunciado_correto_1_ou_0'] for n in notas) != {'1': 40, '0': 10}:
        raise ValueError("Resultado historico da auditoria foi alterado")

    catalogo_file = sem4.TRANSCRICOES
    catalogo = sem4.transcricoes_validas(json.loads(catalogo_file.read_text(encoding='utf-8')))
    sem4.validar_percentuais(catalogo)
    expected_rasc = {n['id'] for n in notas if n.get('tipo') == 'discursiva' and n['enunciado_correto_1_ou_0'] == '0'}
    if len(expected_rasc) != 2:
        raise ValueError("Esperadas duas discursivas com limpeza de RASCUNHO")
    tratados = set()
    changed_clean = set()
    assets_all = set()
    out2023 = []
    for orig in original:
        ident = orig['id']
        qc, q = c_by[ident], s_by[ident]
        key = (q.get('curso'), q.get('numero_questao'))
        for fiel in ("id", "ano", "curso", "numero_questao", "tipo_questao", "origem", "alternativas", "gabarito"):
            if qc.get(fiel) != orig.get(fiel) or q.get(fiel) != orig.get(fiel):
                raise ValueError(f"Fonte do campo {fiel} modificada: {ident[:12]}")
        if ident in expected_rasc:
            cleaned = limpar_rascunho(orig['enunciado'])
            if cleaned is None or qc['enunciado'] != cleaned:
                raise ValueError(f"Rascunho nao foi limpo conforme regra validada: {ident[:12]}")
            changed_clean.add(ident)
        elif orig.get('enunciado') != qc.get('enunciado'):
            raise ValueError(f"Enunciado fora dos dois rascunhos foi alterado: {ident[:12]}")
        if q.get('enunciado') != qc.get('enunciado'):
            raise ValueError(f"Enunciado semantico nao preserva o texto da derivacao: {ident[:12]}")

        if key in sem4.CHAVES:
            if key in tratados or not ident.startswith(sem4.IDS_PREFIXO[key]):
                raise ValueError(f"ID inesperado ou questao duplicada: {key}")
            tratados.add(key)
            if notes.get(ident, {}).get('enunciado_correto_1_ou_0') != '0':
                raise ValueError(f"Faltou nota historica reprovando enunciado de {key}")
            details = q.get('semantica_rf04')
            if not isinstance(details, dict) or details.get('estado') != 'RASCUNHO_TECNICO_EXIGE_NOVA_REVISAO_HUMANA':
                raise ValueError(f"Representacao semantica incompleta: {key}")
            row = catalogo[key]
            for campo, esperado in (("titulo",row['titulo']),("tipo",row['tipo_representacao']),
                                    ("pagina_pdf",row['pagina_pdf']),("colunas",row['colunas']),
                                    ("linhas",row['linhas']),("observacao",row['observacao'])):
                if details.get(campo) != esperado:
                    raise ValueError(f"Dados semanticamente alterados: {key}, {campo}")
            references = sem4.midias_verificadas(base, q)
            if details.get('imagens') != references:
                raise ValueError(f"Imagens do catalogo nao conferem: {key}")
            for r in references:
                assets_all.add(r['arquivo'])
            if key == ("Arquitetura e Urbanismo",11) and {r.get('letra') for r in references if r.get('letra')} != set('ABCDE'):
                raise ValueError("As cinco alternativas graficas precisam estar presentes")
            orig_sem = deepcopy(q)
            orig_sem.pop('semantica_rf04')
            orig_sem.pop('apresentacao_visual_rf04',None)
            orig_sem['pendente_revisao'] = qc['pendente_revisao']
            orig_sem['alertas'] = qc['alertas']
            if orig_sem != qc:
                raise ValueError(f"Campos nao autorizados alterados no RF04: {key}")
        elif q != qc:
            raise ValueError(f"Questao fora do RF04 foi alterada: {ident[:12]}")
        out2023.append(q)
    if tratados != sem4.CHAVES or changed_clean != expected_rasc or len(assets_all) != 14:
        raise ValueError("Quantidade de alvos RF04, rascunhos ou imagens inesperada")
    if Counter(str(q['ano']) for q in out2023) != {'2023': 80}:
        raise ValueError("Anos do lote 2023 invalidos")
    if Counter(str(q['ano']) for q in antiga) != {'2017':80,'2021':120}:
        raise ValueError("Anos do lote 2017/2021 invalidos")
    all_ids = [q['id'] for q in out2023+antiga]
    if len(set(all_ids)) != 280:
        raise ValueError("Duplicacao de IDs entre 2023 e 2017/2021")
    fontes = {str(p).replace('\\','/'): v3.sha_file(base / p) for p in
              (ORIGINAL_2023,FONTE_2023_CLEAN,FONTE_2023,FONTE_ANTIGA,CSV)}
    fontes["docs/RF04_TRANSCRICOES_ESTRUTURADAS.json"] = v3.sha_file(catalogo_file)
    for q in out2023+antiga:
        v3.validar_questao(q)
    return out2023, antiga, fontes, expected_rasc


def chaves_aprovacao(fontes: dict) -> dict:
    return {k:fontes[k] for k in (str(FONTE_2023).replace('\\','/'),
                                   str(CSV).replace('\\','/'),
                                   'docs/RF04_TRANSCRICOES_ESTRUTURADAS.json')}


def registrar_aprovacao(base: Path, declaracao: str):
    if declaracao.strip().casefold() != FRASE.casefold():
        raise ValueError(f"Para registrar a revisao forneca exatamente: {FRASE}")
    _, _, fontes, _ = preparar_fontes(base)
    corpo = {
        'escopo': 'OITO_REPRESENTACOES_SEMANTICAS_RF04_ENADE_2023',
        'resultado': 'APROVADO_PELO_REVISOR_EM_NOVA_CONFERENCIA',
        'declaracao': declaracao,
        'origem_declaracao': 'confirmacao_explicita_do_usuario_na_conversa',
        'data_registro_utc': agora(),
        'origem_auditoria_50': 'preservada_sem_alteracao',
        'outros_272_registros': 'nao_aprovados_por_esta_declaracao',
        'fonte_hashes': chaves_aprovacao(fontes),
        'observacao': 'Aprovacao apenas da representacao semantica adicional de 8 questoes; nao certifica 280 questoes completas nem Kerberos.'
    }
    if APROVACAO.exists():
        anterior=json.loads(APROVACAO.read_text(encoding='utf-8'))
        if anterior.get('fonte_hashes') != corpo['fonte_hashes'] or anterior.get('resultado') != corpo['resultado']:
            raise ValueError('Existe aprovacao vinculada a arquivos diferentes; nao sobrescrever')
        return anterior
    salvar(APROVACAO, corpo)
    return corpo


def carregar_aprovacao(fontes: dict):
    if not APROVACAO.is_file():
        raise ValueError('Falta evidencia de aceite: execute registrar-aprovacao primeiro')
    x=json.loads(APROVACAO.read_text(encoding='utf-8'))
    if x.get('resultado') != 'APROVADO_PELO_REVISOR_EM_NOVA_CONFERENCIA' or x.get('fonte_hashes') != chaves_aprovacao(fontes):
        raise ValueError('Evidencia editorial nao corresponde aos dados atuais')
    return x


def preparar(base: Path, *, persist: bool = False):
    dados2023, antigos, fontes, rasc = preparar_fontes(base)
    aprovado = carregar_aprovacao(fontes)
    items = deepcopy(dados2023 + antigos)
    for q in items:
        q['pendente_revisao']=True
        q['revisado_humanamente']=False
        q['status_validacao']='nao_revisada'
        q['origem_avaliacao']='nao_confirmada'
        alerts=q.setdefault('alertas',[])
        if not isinstance(alerts,list):
            raise ValueError('Alertas nao e lista')
        if 'pendente_validacao_editorial' not in alerts:
            alerts.append('pendente_validacao_editorial')
        if 'semantica_rf04' in q:
            info=q['semantica_rf04']
            info['estado']='APROVADA_EM_NOVA_CONFERENCIA_HUMANA'
            q['rf04_aprovacao_status']='APROVADA_APENAS_REPRESENTACAO'
            q['rf04_aprovacao_evidencia']='evidencias/A3_rf04_aprovacao_editorial_8.json'
            if 'rf04_transcricao_estruturada_a_conferir' in alerts:
                alerts.remove('rf04_transcricao_estruturada_a_conferir')
        v3.validar_questao(q)
    anos=Counter(str(q['ano']) for q in items)
    if len(items)!=280 or len({q['id'] for q in items})!=280 or anos != {'2017':80,'2021':120,'2023':80}:
        raise ValueError('280 IDs/anos inconsistentes')
    n_sem=sum('semantica_rf04' in q for q in items)
    if n_sem!=8:
        raise ValueError('Devem existir oito representacoes aprovadas')
    resultado={'resultado':'PREFLIGHT_APROVADO_PARA_INDICE_NOVO', 'indice':INDICE,
        'topico':TOPICO,'total':len(items),'ids_unicos':len({q['id'] for q in items}),
        'por_ano':dict(sorted(anos.items())), 'representacoes_semanticas_aprovadas':n_sem,
        'rascunhos_discursivos_limpos':len(rasc), 'auditoria_historica_alterada':False,
        'escopo_aprovacao':'apenas_as_8_representacoes_semanticas',
        'status_global_280':'RASCUNHO_TECNICO', 'kerberos':'NAO_IMPLEMENTADO',
        'fontes_sha256': fontes, 'aprovacao_sha256':v3.sha_file(APROVACAO),
        'avisos':['2017/2021 ainda exigem revisao editorial',
                  'Imagens sao arquivos locais; Elasticsearch guarda referencias, nao o binario dos PNGs',
                  'Nao altera indice v1/v2/v3 nem o CSV original']}
    if persist:
        output = base / DATA_V4
        output.parent.mkdir(parents=True,exist_ok=True)
        tmp=output.with_suffix('.jsonl.tmp')
        tmp.write_text(''.join(json.dumps(q,ensure_ascii=False,sort_keys=True)+'\n' for q in items),encoding='utf-8')
        os.replace(tmp,output)
        resultado['jsonl_v4']=str(DATA_V4).replace('\\','/')
        resultado['sha256_jsonl_v4']=v3.sha_file(output)
        salvar(PREFLIGHT,resultado)
    return items, resultado


def mapa_v4():
    from enade_pipeline.integracao import MAPPING
    x=deepcopy(MAPPING)
    x['mappings']['properties'].update({
        'status_validacao':{'type':'keyword'},'revisado_humanamente':{'type':'boolean'},
        'origem_avaliacao':{'type':'keyword'},
        'rf04_aprovacao_status':{'type':'keyword'},
        'rf04_aprovacao_evidencia':{'type':'keyword'},
        'semantica_rf04':{'type':'object','enabled':False},
        'apresentacao_visual_rf04':{'type':'object','enabled':False},
    })
    return x


def snapshot(es, index: str):
    if not es.indices.exists(index=index):
        raise ValueError(f'Indice anterior ausente: {index}')
    count = es.count(index=index)['count']
    if count > 10000:
        raise ValueError('O indice excedeu o limite de verificacao segura de 10000 documentos')
    hits=es.search(index=index,query={'match_all':{}},size=max(1,count))['hits']['hits']
    if len(hits)!=count:
        raise ValueError(f'Indice {index}: contagem/search divergentes')
    hashes=sorted((h['_id'],sha_canon(h['_source'])) for h in hits)
    d=sha_bytes(json.dumps(hashes,separators=(',',':')).encode('utf-8'))
    return {'count':count,'sha256_id_e_documento':d}


def snapshots_anteriores(es):
    return {name:snapshot(es,name) for name in ANTERIORES}


def compara_indice(es, items):
    ids = {q['id']:sha_canon(q) for q in items}
    if not es.indices.exists(index=INDICE):
        return {'existe':False,'contagem':0,'presentes':0,'faltantes':280,'divergentes':[]}
    es.indices.refresh(index=INDICE)
    count = es.count(index=INDICE)['count']
    if count>280:
        raise ValueError('Indice v4 contem mais de 280 documentos; interrompido')
    docs=es.mget(index=INDICE,body={'ids':list(ids)})['docs']
    presentes=0; divergentes=[]
    for doc in docs:
        if doc.get('found'):
            presentes+=1
            if sha_canon(doc['_source'])!=ids[doc['_id']]:
                divergentes.append(doc['_id'])
    if count != presentes:
        raise ValueError('Indice v4 possui documentos desconhecidos; nao alterar')
    if divergentes:
        raise ValueError('Indice v4 possui documentos divergentes; nao sobrescrever: '+','.join(x[:12] for x in divergentes[:5]))
    return {'existe':True,'contagem':count,'presentes':presentes,'faltantes':280-presentes,'divergentes':[]}


def instalar(es,kafka_url):
    from kafka.admin import KafkaAdminClient
    admin=KafkaAdminClient(bootstrap_servers=kafka_url,client_id='enade-v4-setup',request_timeout_ms=30000)
    try:
        v3.ensure_topic(admin,TOPICO,3)
        v3.ensure_topic(admin,TOPICO_DLQ,1)
    finally:
        admin.close()
    if not es.indices.exists(index=INDICE):
        es.indices.create(index=INDICE,body=mapa_v4())


def publicar(kafka_url, items):
    from kafka import KafkaProducer
    prod=KafkaProducer(bootstrap_servers=kafka_url,acks='all',retries=4,
                        max_in_flight_requests_per_connection=1,request_timeout_ms=30000)
    try:
        for q in items:
            prod.send(TOPICO,key=q['id'].encode('ascii'),value=v3.encode(q)).get(timeout=45)
        prod.flush(timeout=30)
    finally:
        prod.close(timeout=15)
    return len(items)


def consumir(kafka_url,es,items,timeout):
    from kafka import KafkaConsumer, KafkaProducer, TopicPartition
    from kafka.structs import OffsetAndMetadata
    byid={q['id']:sha_canon(q) for q in items}
    consumer=KafkaConsumer(TOPICO,bootstrap_servers=kafka_url,
                           group_id='enade-v4-rf04-'+uuid.uuid4().hex[:16],
                           enable_auto_commit=False, auto_offset_reset='earliest',
                           max_poll_records=100)
    dlq=KafkaProducer(bootstrap_servers=kafka_url,acks='all',retries=4,
                      max_in_flight_requests_per_connection=1,request_timeout_ms=30000)
    contagem={'indexados':0,'dlq':0}
    def commit(event):
        consumer.commit(offsets={TopicPartition(event.topic,event.partition):
                                 OffsetAndMetadata(event.offset+1,'',-1)})
    try:
        fim=time.monotonic()+timeout
        while time.monotonic()<fim:
            lotes=consumer.poll(timeout_ms=1000,max_records=100)
            for _,events in lotes.items():
                for event in events:
                    try:
                        msg=json.loads(event.value.decode('utf-8'))
                    except (ValueError,UnicodeDecodeError):
                        msg=None
                    if not isinstance(msg,dict) or msg.get('id') not in byid or sha_canon(msg)!=byid[msg['id']]:
                        raise ValueError('Topico Kafka v4 contem mensagem inesperada; nao confirmar offset')
                    ret=v3.process_message(event,es=es,dlq_producer=dlq,
                                            commit_offset=commit,index=INDICE,dlq_topic=TOPICO_DLQ)
                    contagem['dlq' if ret=='dlq' else 'indexados']+=1
            if contagem['dlq']:
                raise RuntimeError('Algum evento foi enviado a DLQ, indexacao nao aprovada')
            if contagem['indexados']>=280:
                es.indices.refresh(index=INDICE)
                if compara_indice(es,items)['faltantes']==0:
                    break
        es.indices.refresh(index=INDICE)
    finally:
        consumer.close()
        dlq.close(timeout=15)
    return contagem


def verificar(es,items,report,before=None,events=None):
    result = compara_indice(es,items)
    after=snapshots_anteriores(es)
    before=before or after
    preservados=(after==before)
    correto=(result['contagem']==280 and result['presentes']==280
             and result['faltantes']==0 and preservados)
    rel={'resultado':'APROVADO' if correto else 'REPROVADO',
         'indice':INDICE,'topico':TOPICO,'ids_presentes':result['presentes'],
         'ids_faltantes':result['faltantes'],'contagem':result['contagem'],
         'comparacao_integral_documentos':len(result['divergentes'])==0,
         'indice_v1_v2_v3_preservados':preservados,
         'snapshot_anteriores_antes':before,'snapshot_anteriores_depois':after,
         'publicacao_consumo':events,
         'sha256_280':report.get('sha256_jsonl_v4'),
         'representacoes_rf04_conferidas':8,
         'status_global':'RASCUNHO_TECNICO_FORA_DA_REVISAO_RF04',
         'kerberos':'NAO_IMPLEMENTADO',
         'observacao':'Aprovacao apenas das oito representacoes RF04; 2017/2021 e outras validacoes seguem pendentes.'}
    salvar(VERIFICACAO,rel)
    print(json.dumps(rel,ensure_ascii=False,indent=2))
    if not correto:
        raise RuntimeError('Verificacao do indice v4 reprovada')
    return rel


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('acao',choices=('registrar-aprovacao','preflight','executar','verificar'))
    p.add_argument('--origem',type=Path,default=ROOT.parent/'ENADE BigData II Projeto')
    p.add_argument('--declaracao',default='')
    p.add_argument('--elastic',default='http://127.0.0.1:9200')
    p.add_argument('--kafka',default='127.0.0.1:29092')
    p.add_argument('--timeout',type=int,default=180)
    args=p.parse_args()
    try:
        origem=args.origem.resolve()
        if args.acao=='registrar-aprovacao':
            res=registrar_aprovacao(origem,args.declaracao)
            print(json.dumps(res,ensure_ascii=False,indent=2))
            return 0
        items,rep=preparar(origem,persist=args.acao in ('preflight','executar','verificar'))
        print(json.dumps(rep,ensure_ascii=False,indent=2))
        if args.acao=='preflight':
            print('PREFLIGHT V4 APROVADO - NENHUM INDICE OU TOPICO MODIFICADO')
            return 0
        es=v3.elastic_client(args.elastic)
        try:
            before=snapshots_anteriores(es)
            if args.acao=='executar':
                state=compara_indice(es,items)
                if state['faltantes']:
                    instalar(es,args.kafka)
                    enviados=publicar(args.kafka,items)
                    proc=consumir(args.kafka,es,items,args.timeout)
                    eventos={'enviados_ack':enviados,**proc}
                else:
                    eventos={'idempotente':True,'eventos_novos':0}
            else:
                eventos={'apenas_verificacao':True}
            verificar(es,items,rep,before,events=eventos)
        finally:
            es.close()
        return 0
    except Exception as exc:
        print(f'ERRO: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
