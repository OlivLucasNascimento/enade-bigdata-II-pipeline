#!/usr/bin/env python3
"""Prepara e indexa 280 questões do ENADE em v3, sem modificar v1/v2.

Fontes (no projeto LOCAL, fora do Git):
- 80 questões de 2023: data/extraidos/questoes_com_midias.jsonl
- 200 questões de 2017/2021: data/extraidos_2017_2021_corrigidos/questoes.jsonl

Sempre em status rascunho: indexação técnica não substitui revisão humana.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import copy
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from enade_pipeline.integracao import MAPPING, encode, validar_questao

INDEX = 'enade-questoes-v3'
TOPIC = 'enade.questoes.v3'
DLQ_TOPIC = 'enade.questoes.v3.dlq'
BASE_ORIGEM = ROOT.parent / 'ENADE BigData II Projeto'
INPUTS = (
    ('2023', Path('data/extraidos/questoes_com_midias.jsonl'), 80),
    ('2017-2021', Path('data/extraidos_2017_2021_corrigidos/questoes.jsonl'), 200),
)


def sha_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for piece in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(piece)
    return sha.hexdigest()


def digest_json(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def read_jsonl(file: Path) -> list[dict]:
    if not file.is_file():
        raise FileNotFoundError(f'Arquivo de origem ausente: {file}')
    result = []
    for i, line in enumerate(file.read_text(encoding='utf-8-sig').splitlines(), 1):
        if line.strip():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f'JSON invalido em {file.name}, linha {i}: {exc}') from exc
            if not isinstance(obj, dict):
                raise ValueError(f'Registro nao-objeto em {file.name}, linha {i}')
            result.append(obj)
    return result


def prepare(base: Path, *, persist: bool = True):
    all_items: list[dict] = []
    sources = []
    for label, relative, expected in INPUTS:
        source = base / relative
        items = read_jsonl(source)
        if len(items) != expected:
            raise ValueError(f'Lote {label}: esperado {expected}, obtido {len(items)}')
        actual_years = Counter(str(q.get('ano')) for q in items)
        if label == '2023' and actual_years != {'2023': 80}:
            raise ValueError(f'Anos incorretos no lote 2023: {dict(actual_years)}')
        if label == '2017-2021' and actual_years != {'2017': 80, '2021': 120}:
            raise ValueError(f'Anos incorretos no lote 2017/2021: {dict(actual_years)}')
        sources.append({'lote': label, 'arquivo': relative.as_posix(),
                        'quantidade': len(items), 'sha256': sha_file(source)})
        all_items.extend(items)

    seen = set()
    for i, entry in enumerate(all_items, 1):
        item = copy.deepcopy(entry)
        validar_questao(item)
        if item['id'] in seen:
            raise ValueError(f'ID duplicado ENTRE LOTES: {item["id"]}')
        seen.add(item['id'])
        # Os dois conjuntos nao contam com aceite editorial formal.
        # Forcar rascunho sem modificar o JSONL-fonte.
        item['pendente_revisao'] = True
        item['revisado_humanamente'] = False
        item['status_validacao'] = 'nao_revisada'
        item['origem_avaliacao'] = 'nao_confirmada'
        alertas = item.get('alertas')
        if not isinstance(alertas, list):
            raise ValueError(f'alertas nao e lista para {item["id"]}')
        if 'pendente_validacao_editorial' not in alertas:
            alertas.append('pendente_validacao_editorial')
        validar_questao(item)
        all_items[i-1] = item

    years = Counter(str(q['ano']) for q in all_items)
    if len(all_items) != 280 or len(seen) != 280 or years != {'2017': 80, '2021': 120, '2023': 80}:
        raise ValueError(f'Inconsistencia em 280 registros: {len(all_items)}, {len(seen)}, {dict(years)}')
    report = {
        'resultado': 'PREFLIGHT_OK_RASCUNHO', 'indice': INDEX, 'topico': TOPIC,
        'total': 280, 'ids_unicos': 280, 'por_ano': dict(sorted(years.items())),
        'status_validacao': 'nao_revisada', 'revisao_humana': 'PENDENTE',
        'fontes': sources, 'dados_locais_incluidos_no_git': False,
        'aviso': 'Indexacao tecnica. Gabaritos, graficos e qualidade editorial exigem conferencia adicional.',
    }
    if persist:
        output = base / 'data/extraidos_280_v3/questoes.jsonl'
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8', newline='\n') as f:
            for entry in all_items:
                f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + '\n')
        report['arquivo_gerado'] = 'data/extraidos_280_v3/questoes.jsonl'
        report['sha256_280'] = sha_file(output)
        save_report(ROOT / 'evidencias/A4_v3_preflight.json', report)
    return all_items, report


def save_report(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def elastic_client(url: str):
    from elasticsearch import Elasticsearch
    es = Elasticsearch(url, request_timeout=30, max_retries=2, retry_on_timeout=True)
    if not es.ping():
        raise RuntimeError(f'Elasticsearch indisponivel em {url}')
    return es


def ensure_topic(admin, name: str, partitions: int):
    """Cria um topico ausente; nao recria nem altera topicos existentes."""
    from kafka.admin import NewTopic
    from kafka.errors import TopicAlreadyExistsError
    try:
        admin.create_topics([NewTopic(name=name, num_partitions=partitions, replication_factor=1)])
    except TopicAlreadyExistsError:
        pass


def configure_dlq(kafka_url: str):
    """Prepara somente a DLQ v3, sem republicar as 280 questoes."""
    from kafka.admin import KafkaAdminClient
    admin = KafkaAdminClient(bootstrap_servers=kafka_url, client_id='enade-v3-dlq-setup', request_timeout_ms=30000)
    try:
        ensure_topic(admin, DLQ_TOPIC, 1)
    finally:
        admin.close()
    print(f'DLQ configurada: {DLQ_TOPIC} (sem modificar os indices)')


def process_message(event, *, es, dlq_producer, commit_offset,
                    index: str = INDEX, dlq_topic: str = DLQ_TOPIC):
    """Processa um evento e so confirma offset apos ES ou ACK de DLQ.

    Erros de esquema/JSON seguem para DLQ. Falhas de infraestrutura
    (Elasticsearch, publicacao na DLQ, commit) sao propagadas: nao ha
    confirmacao antecipada e o Kafka pode reentregar a mensagem.
    """
    raw = event.value
    try:
        q = validar_questao(json.loads(raw.decode('utf-8')))
        if q.get('status_validacao') != 'nao_revisada' or q.get('revisado_humanamente') is not False:
            raise ValueError('evento sem classificacao rascunho segura')
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        # Preservar os bytes do evento permite examinar/reprocessar o original.
        content_sha = hashlib.sha256(raw).hexdigest()
        envelope = {
            'erro_tipo': type(exc).__name__,
            'erro': str(exc)[:600],
            'evento_sha256': content_sha,
            'evento_base64': base64.b64encode(raw).decode('ascii'),
            'origem': {'topico': event.topic, 'particao': event.partition,
                       'offset': event.offset},
            'registrado_em_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'status': 'invalido',
        }
        # get espera ACK real, acks='all' no producer. Se falhar, NAO confirma offset.
        dlq_producer.send(dlq_topic, key=content_sha.encode('ascii'),
                          value=encode(envelope)).get(timeout=45)
        commit_offset(event)
        return 'dlq'
    # Falha de ES nao e erro de dados. Nao enviar a DLQ nem confirmar offset.
    es.index(index=index, id=q['id'], document=q)
    commit_offset(event)
    return 'indexado'


def setup(kafka_url: str, es):
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError
    admin = KafkaAdminClient(bootstrap_servers=kafka_url, client_id='enade-v3-setup', request_timeout_ms=30000)
    try:
        ensure_topic(admin, TOPIC, 3)
        ensure_topic(admin, DLQ_TOPIC, 1)
    finally:
        admin.close()
    if not es.indices.exists(index=INDEX):
        mapping = copy.deepcopy(MAPPING)
        mapping['mappings']['properties'].update({
            'status_validacao': {'type': 'keyword'},
            'revisado_humanamente': {'type': 'boolean'},
            'origem_avaliacao': {'type': 'keyword'},
        })
        es.indices.create(index=INDEX, body=mapping)
        print('Indice v3 criado, v1 e v2 preservados')
    else:
        print('Indice v3 ja existe: nenhuma exclusao sera realizada')


def publish(kafka_url: str, items: list[dict]):
    from kafka import KafkaProducer
    p = KafkaProducer(bootstrap_servers=kafka_url, acks='all', retries=4,
                      max_in_flight_requests_per_connection=1,
                      request_timeout_ms=30000)
    try:
        for q in items:
            p.send(TOPIC, key=q['id'].encode('ascii'), value=encode(q)).get(timeout=45)
        p.flush(timeout=30)
    finally:
        p.close(timeout=15)
    print(f'ACK confirmado para {len(items)} eventos em {TOPIC}')


def compare(es, items: list[dict]):
    desired = {q['id']: digest_json(q) for q in items}
    docs = es.mget(index=INDEX, body={'ids': list(desired)})['docs']
    found, different = set(), []
    for doc in docs:
        if doc.get('found'):
            found.add(doc['_id'])
            if digest_json(doc['_source']) != desired[doc['_id']]:
                different.append(doc['_id'])
    return len(found), len(desired) - len(found), different


def consume(kafka_url: str, es, items: list[dict], timeout: int = 120):
    from kafka import KafkaConsumer, KafkaProducer, TopicPartition
    from kafka.structs import OffsetAndMetadata
    # Grupo atrelado ao corpus, evita colisoes com v1/v2.
    checksum = hashlib.sha256('|'.join(sorted(q['id'] for q in items)).encode('ascii')).hexdigest()[:12]
    group = f'enade-indexador-v3-{checksum}'
    c = KafkaConsumer(TOPIC, bootstrap_servers=kafka_url, group_id=group,
                      enable_auto_commit=False, auto_offset_reset='earliest', max_poll_records=100)
    dlq_producer = KafkaProducer(bootstrap_servers=kafka_url, acks='all', retries=4,
                                 max_in_flight_requests_per_connection=1,
                                 request_timeout_ms=30000)
    counts = {'indexado': 0, 'dlq': 0}
    end = time.monotonic() + timeout

    def commit_offset(event):
        c.commit(offsets={TopicPartition(event.topic, event.partition):
                          OffsetAndMetadata(event.offset + 1, '', -1)})

    try:
        while time.monotonic() < end:
            batches = c.poll(timeout_ms=1000, max_records=100)
            for tp, msgs in batches.items():
                for event in msgs:
                    result = process_message(event, es=es, dlq_producer=dlq_producer,
                                             commit_offset=commit_offset)
                    counts[result] += 1
            if not batches:
                es.indices.refresh(index=INDEX)
                _, missing, outdated = compare(es, items)
                if not missing and not outdated:
                    break
        es.indices.refresh(index=INDEX)
        print('Eventos processados nesta execucao: '
              f'indexados={counts["indexado"]}, DLQ={counts["dlq"]}')
    finally:
        c.close()
        dlq_producer.close(timeout=15)
    return counts


def verify(es, items: list[dict], report: dict):
    es.indices.refresh(index=INDEX)
    count = es.count(index=INDEX)['count']
    present, missing, different = compare(es, items)
    result = {
        'resultado': 'APROVADO' if (count == 280 and present == 280 and not missing and not different) else 'REPROVADO',
        'indice': INDEX, 'topico': TOPIC, 'contagem': count,
        'ids_presentes': present, 'ids_faltantes': missing,
        'ids_divergentes': different[:20], 'quantidade_divergentes': len(different),
        'situacao': 'RASCUNHO_NAO_REVISADO', 'kerberos': 'NAO_IMPLEMENTADO',
        'preservacao': 'Sem operacoes de escrita nos indices v1 e v2',
        'fontes': report['fontes'], 'sha256_280': report.get('sha256_280'),
    }
    save_report(ROOT / 'evidencias/A4_v3_verificacao.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result['resultado'] != 'APROVADO':
        raise RuntimeError('Verificacao v3 falhou: consulte evidencias/A4_v3_verificacao.json')


def main():
    p = argparse.ArgumentParser(description='ENADE 280 questoes: preflight e indexacao v3 segura')
    p.add_argument('acao', choices=('preflight', 'executar', 'verificar', 'configurar-dlq'))
    p.add_argument('--origem', type=Path, default=BASE_ORIGEM, help='Pasta original com data/extraidos...')
    p.add_argument('--kafka', default='127.0.0.1:29092')
    p.add_argument('--elastic', default='http://127.0.0.1:9200')
    p.add_argument('--timeout', type=int, default=120)
    args = p.parse_args()
    try:
        if args.acao == 'configurar-dlq':
            configure_dlq(args.kafka)
            return 0
        items, report = prepare(args.origem.resolve())
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.acao == 'preflight':
            print('PREFLIGHT APROVADO: Kafka e Elasticsearch nao foram alterados.')
            return 0
        es = elastic_client(args.elastic)
        try:
            if args.acao == 'executar':
                setup(args.kafka, es)
                publish(args.kafka, items)
                consume(args.kafka, es, items, timeout=args.timeout)
            elif not es.indices.exists(index=INDEX):
                raise RuntimeError('Indice v3 nao existe; execute a acao executar')
            verify(es, items, report)
        finally:
            es.close()
        return 0
    except Exception as exc:
        print(f'ERRO: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
