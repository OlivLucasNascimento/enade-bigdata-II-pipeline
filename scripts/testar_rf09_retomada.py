#!/usr/bin/env python3
"""Teste REAL de retomada do consumidor após falha simulada antes do commit.

Usa tópico e índice temporários próprios; não altera o v1, o v2 nem os grupos
originais. Exige Kafka e Elasticsearch locais saudáveis. Não valida Kerberos.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enade_pipeline.integracao import MAPPING, validar_questao, encode


def ler_evento(consumer, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        batches = consumer.poll(timeout_ms=1000, max_records=1)
        for records in batches.values():
            if records:
                return records[0]
    raise RuntimeError('Nenhum evento recebido dentro do prazo; confira grupo e broker')


def testar(base: Path, kafka: str, elastic: str):
    from kafka import KafkaConsumer, KafkaProducer, TopicPartition
    from kafka.structs import OffsetAndMetadata
    from kafka.admin import KafkaAdminClient, NewTopic
    from elasticsearch import Elasticsearch
    token = uuid.uuid4().hex[:10]
    topic = f'enade.rf09.retomada.{token}'
    group = f'enade-rf09-grupo-{token}'
    index = f'enade-rf09-{token}'
    arq = base / 'data/extraidos/questoes_com_midias.jsonl'
    with arq.open(encoding='utf-8') as file:
        q = validar_questao(json.loads(next(line for line in file if line.strip())))
    admin = KafkaAdminClient(bootstrap_servers=kafka)
    es = Elasticsearch(elastic, request_timeout=25)
    producer = None
    c1 = c2 = None
    try:
        if not es.ping(): raise RuntimeError('Elasticsearch não responde')
        admin.create_topics([NewTopic(name=topic, num_partitions=1, replication_factor=1)])
        es.indices.create(index=index, body=copy.deepcopy(MAPPING))
        producer = KafkaProducer(bootstrap_servers=kafka, acks='all')
        metadata = producer.send(topic, key=q['id'].encode('ascii'), value=encode(q)).get(timeout=45)
        producer.flush(timeout=30)
        config = dict(bootstrap_servers=kafka, group_id=group, enable_auto_commit=False,
                      auto_offset_reset='earliest', max_poll_records=1)
        c1 = KafkaConsumer(topic, **config)
        first = ler_evento(c1)
        if first.value != encode(q): raise RuntimeError('Mensagem alterada no Kafka antes do teste')
        es.index(index=index, id=q['id'], document=q, refresh='wait_for')
        before = es.count(index=index)['count']
        if before != 1: raise RuntimeError('Falha no primeiro indexamento do teste')
        # Simulação de crash: close sem commit APÓS gravar no Elasticsearch.
        c1.close(); c1 = None
        c2 = KafkaConsumer(topic, **config)
        retried = ler_evento(c2)
        if (retried.topic, retried.partition, retried.offset) != (first.topic, first.partition, first.offset):
            raise RuntimeError('Retomada não repetiu a mensagem sem commit')
        q2 = validar_questao(json.loads(retried.value.decode('utf-8')))
        es.index(index=index, id=q2['id'], document=q2, refresh='wait_for')
        c2.commit(offsets={TopicPartition(retried.topic, retried.partition):
                           OffsetAndMetadata(retried.offset + 1, '', -1)})
        after = es.count(index=index)['count']
        if after != 1: raise RuntimeError('Duplicação detectada após retomada')
        output = dict(
            requisito='RF09_RF10', resultado='APROVADO',
            cenario='falha apos indexar no Elasticsearch e antes de confirmar o offset Kafka',
            topico_teste=topic, indice_teste=index, grupo_teste=group,
            particao=metadata.partition, offset_original=first.offset,
            offset_reprocessado=retried.offset, documentos_antes=before,
            documentos_depois=after, ids_preservados=first.key == retried.key,
            data_utc=datetime.now(timezone.utc).isoformat(),
            observacao='Teste isolado, sem Kerberos e sem apagar tópicos ou índices de produção.'
        )
        evid = base / 'evidencias'; evid.mkdir(exist_ok=True)
        (evid / 'A5_rf09_retomada_consumidor.json').write_text(
            json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(output, ensure_ascii=False, indent=2))
    finally:
        for item in (c1, c2):
            if item is not None: item.close()
        if producer is not None: producer.close()
        admin.close()
        es.close()


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--base', type=Path, default=ROOT)
    a.add_argument('--kafka', default='127.0.0.1:29092')
    a.add_argument('--elastic', default='http://127.0.0.1:9200')
    o = a.parse_args()
    try:
        testar(o.base.resolve(), o.kafka, o.elastic)
        return 0
    except Exception as ex:
        print(f'ERRO {type(ex).__name__}: {ex}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
