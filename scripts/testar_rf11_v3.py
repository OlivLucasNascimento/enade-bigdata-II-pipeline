#!/usr/bin/env python3
"""Teste RF11 REAL isolado: 2 invalidos -> DLQ; 1 valido -> indice isolado.

Nao publica nem consome no topico enade.questoes.v3, nem escreve nos
indices enade-questoes-v1/v2/v3. Deixa topicos/indice de teste para auditoria.
"""
from __future__ import annotations
import base64
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.indexar_v3 import (INDEX, DLQ_TOPIC, MAPPING, encode,
                                ensure_topic, process_message, save_report)


def snapshot(es):
    result = {}
    for name in ('enade-questoes-v1', 'enade-questoes-v2', INDEX):
        result[name] = es.count(index=name)['count'] if es.indices.exists(index=name) else None
    return result


def run(kafka_url='127.0.0.1:29092', elastic_url='http://127.0.0.1:9200'):
    from elasticsearch import Elasticsearch
    from kafka import KafkaProducer, KafkaConsumer, TopicPartition
    from kafka.admin import KafkaAdminClient
    from kafka.structs import OffsetAndMetadata
    suffix = uuid.uuid4().hex[:12]
    topic = f'enade.rf11.v3.validacao.{suffix}'
    dlq_topic = f'enade.rf11.v3.dlq.{suffix}'
    test_index = f'enade-rf11-v3-teste-{suffix}'
    es = Elasticsearch(elastic_url, request_timeout=30)
    if not es.ping():
        raise RuntimeError('Elasticsearch indisponivel')
    before = snapshot(es)
    if before[INDEX] != 280:
        raise RuntimeError(f'Index v3 nao tem 280 documentos: {before[INDEX]}')
    raw_bad_json = b'{evento-invalido'
    raw_bad_schema = b'{"id":"sem-campos-obrigatorios"}'
    obj = {
        'id': hashlib.sha256(('teste-rf11-'+suffix).encode()).hexdigest(),
        'ano': 2021, 'area': 'Computacao', 'curso': 'RF11 TESTE ISOLADO',
        'tipo_formacao': 'CE', 'numero_questao': 1, 'tipo_questao': 'objetiva',
        'enunciado': 'Mensagem sintetica para testar DLQ, NAO OFICIAL',
        'alternativas': [{'letra': 'A', 'texto': 'Resposta ficticia'}],
        'pendente_revisao': True, 'status_validacao': 'nao_revisada',
        'revisado_humanamente': False,
        'origem': {'pdf_url': 'https://example.org/teste-nao-oficial.pdf',
                   'pdf_sha256': 'a' * 64, 'pagina_inicial': 1, 'pagina_final': 1},
    }
    admin = KafkaAdminClient(bootstrap_servers=kafka_url, request_timeout_ms=30000)
    try:
        ensure_topic(admin, topic, 1)
        ensure_topic(admin, dlq_topic, 1)
    finally:
        admin.close()
    if es.indices.exists(index=test_index):
        raise RuntimeError('Indice isolado ja existe; teste abortado sem alterar dados')
    es.indices.create(index=test_index, body=MAPPING)
    p = KafkaProducer(bootstrap_servers=kafka_url, acks='all', retries=4)
    try:
        for value in (raw_bad_json, raw_bad_schema, encode(obj)):
            p.send(topic, value=value, key=b'RF11').get(timeout=45)
        p.flush(timeout=30)
        c = KafkaConsumer(topic, bootstrap_servers=kafka_url, group_id=f'enade-rf11-teste-{suffix}',
                          enable_auto_commit=False, auto_offset_reset='earliest')
        outcomes = []
        try:
            deadline = time.monotonic() + 60
            while len(outcomes) < 3 and time.monotonic() < deadline:
                for _, batch in c.poll(timeout_ms=1000).items():
                    for event in batch:
                        def commit_offset(e):
                            c.commit(offsets={TopicPartition(e.topic, e.partition):
                                              OffsetAndMetadata(e.offset + 1, '', -1)})
                        outcomes.append(process_message(event, es=es, dlq_producer=p,
                                                        commit_offset=commit_offset,
                                                        index=test_index, dlq_topic=dlq_topic))
            if len(outcomes) != 3:
                raise RuntimeError(f'Somente {len(outcomes)} de 3 eventos foram processados')
        finally:
            c.close()
        es.indices.refresh(index=test_index)
        count = es.count(index=test_index)['count']
        dlq = KafkaConsumer(dlq_topic, bootstrap_servers=kafka_url,
                            group_id=f'enade-rf11-auditoria-{suffix}',
                            enable_auto_commit=False, auto_offset_reset='earliest')
        received = []
        try:
            deadline = time.monotonic() + 60
            while len(received) < 2 and time.monotonic() < deadline:
                for _, batch in dlq.poll(timeout_ms=1000).items():
                    for event in batch:
                        received.append(json.loads(event.value.decode('utf-8')))
        finally:
            dlq.close()
        expected_raw = [raw_bad_json, raw_bad_schema]
        valid_dlq = (len(received) == 2 and
                     [base64.b64decode(x.get('evento_base64', '')) for x in received] == expected_raw and
                     [x.get('origem', {}).get('offset') for x in received] == [0, 1] and
                     all(x.get('erro') and x.get('evento_sha256') == hashlib.sha256(raw).hexdigest()
                         for x, raw in zip(received, expected_raw)))
        after = snapshot(es)
        passed = (outcomes == ['dlq', 'dlq', 'indexado'] and count == 1 and
                  valid_dlq and before == after)
        report = {
            'requisito': 'RF11', 'resultado': 'APROVADO' if passed else 'REPROVADO',
            'topico_teste': topic, 'dlq_teste': dlq_topic, 'indice_teste': test_index,
            'eventos_enviados': 3, 'invalidos_na_dlq': len(received),
            'validos_indexados': count, 'resultados': outcomes,
            'dlq_com_motivo_payload_e_offset': valid_dlq,
            'indices_principais_antes': before, 'indices_principais_depois': after,
            'topico_prod_v3_alterado': False, 'indice_prod_v3_alterado': before != after,
            'nota': 'Teste real local sem Kerberos. Indices/topicos isolados preservados para evidencias.'
        }
        save_report(ROOT / 'evidencias/A5_rf11_v3_dlq.json', report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not passed:
            raise RuntimeError('RF11 reprovado; consultar evidencias/A5_rf11_v3_dlq.json')
    finally:
        p.close(timeout=15)
        es.close()


if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        print(f'ERRO RF11: {type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(2)
