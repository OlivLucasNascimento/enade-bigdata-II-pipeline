#!/usr/bin/env python3
"""A4/A5: inicialização de índice, produtor, consumidor, DLQ e verificação.

RESTRIÇÃO: laboratório LOCAL e sem Kerberos (RF22 PENDENTE).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enade_pipeline.integracao import (INDICE, MAPPING, TOPICO_DADOS, TOPICO_ERRO,
                                       encode, fingerprint, validar_questao)


def elastic(url: str):
    from elasticsearch import Elasticsearch
    return Elasticsearch(url, request_timeout=25, max_retries=3, retry_on_timeout=True)


def ensure_index(url: str) -> None:
    es = elastic(url)
    if not es.ping():
        raise RuntimeError('Elasticsearch indisponível')
    if not es.indices.exists(index=INDICE):
        es.indices.create(index=INDICE, **MAPPING)
        print('Índice criado:', INDICE)
    else:
        print('Índice já existe:', INDICE)


def producer(kafka_url: str):
    from kafka import KafkaProducer
    return KafkaProducer(bootstrap_servers=kafka_url, acks='all', retries=5,
                         max_in_flight_requests_per_connection=1,
                         request_timeout_ms=30000, api_version_auto_timeout_ms=15000)


def publish(filepath: Path, kafka_url: str, limit: int) -> None:
    if not filepath.is_file():
        raise FileNotFoundError(f'JSONL não encontrado: {filepath}')
    p = producer(kafka_url)
    counter = 0
    try:
        for line_no, line in enumerate(filepath.read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip():
                continue
            try:
                q = validar_questao(json.loads(line))
            except (ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f'linha {line_no}: {exc}') from exc
            meta = p.send(TOPICO_DADOS, key=q['id'].encode('ascii'), value=encode(q)).get(timeout=45)
            counter += 1
            print(f'Publicado: id={q["id"][:12]} partição={meta.partition} offset={meta.offset}')
            if limit and counter >= limit:
                break
        p.flush(timeout=30)
    finally:
        p.close(timeout=20)
    print(f'Total publicado com ACK: {counter}')


def send_error(p, raw: bytes, cause: Exception, source: dict):
    event = {
        'erro': f'{type(cause).__name__}: {str(cause)[:500]}',
        'evento_sha256': fingerprint(raw),
        'conteudo_preview': raw[:1500].decode('utf-8', errors='replace'),
        'origem_kafka': source,
        'registrado_em_utc': dt.datetime.now(dt.timezone.utc).isoformat()
    }
    p.send(TOPICO_ERRO, key=event['evento_sha256'].encode('ascii'), value=encode(event)).get(timeout=45)
    p.flush(timeout=20)


def consume(kafka_url: str, elastic_url: str, limit: int) -> None:
    """Consome com poll explícito, aguardando a atribuição de partições.

    Um timeout curto no iterador pode acabar antes do group join no primeiro uso.
    Só confirma offset após indexar ou obter ACK da DLQ.
    """
    from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata

    es = elastic(elastic_url)
    if not es.indices.exists(index=INDICE):
        es.close()
        raise RuntimeError(f'Índice {INDICE} ausente: execute criar-indice')

    c = KafkaConsumer(TOPICO_DADOS, bootstrap_servers=kafka_url,
                      group_id='enade-indexador-v1', enable_auto_commit=False,
                      auto_offset_reset='earliest',
                      max_poll_records=25, value_deserializer=None)
    p = producer(kafka_url)
    ok = invalid = 0
    assigned = False
    start = time.monotonic()
    last_message = start
    try:
        while True:
            now = time.monotonic()
            if not assigned and now - start >= 30:
                raise RuntimeError('Kafka não atribuiu partições ao consumidor em 30s; confira conectividade e grupo.')
            if assigned and now - last_message >= 15:
                print('Sem novas mensagens por 15s; encerrando leitura.')
                break

            remaining = max(1, limit - ok - invalid) if limit else 25
            batches = c.poll(timeout_ms=1000, max_records=min(25, remaining))
            current_assignment = c.assignment()
            if current_assignment and not assigned:
                assigned = True
                # Inicia contagem de ociosidade depois da atribuição, não antes.
                last_message = time.monotonic()
                print('Partições atribuídas:', ', '.join(str(tp.partition) for tp in sorted(current_assignment, key=lambda x: x.partition)))
                for tp in sorted(current_assignment, key=lambda x: x.partition):
                    print(f'Partição {tp.partition}: posição={c.position(tp)}, fim={c.end_offsets([tp])[tp]}')

            if not batches:
                continue

            for _, msgs in batches.items():
                for m in msgs:
                    raw = m.value
                    try:
                        q = validar_questao(json.loads(raw.decode('utf-8')))
                    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                        send_error(p, raw, exc, {'topico': m.topic, 'particao': m.partition, 'offset': m.offset})
                        invalid += 1
                        c.commit(offsets={TopicPartition(m.topic, m.partition): OffsetAndMetadata(m.offset + 1, '', -1)})
                        print(f'Inválido -> DLQ, partição={m.partition}, offset={m.offset}, causa={exc}')
                    else:
                        es.index(index=INDICE, id=q['id'], document=q, refresh='wait_for')
                        ok += 1
                        c.commit(offsets={TopicPartition(m.topic, m.partition): OffsetAndMetadata(m.offset + 1, '', -1)})
                        print(f'Indexado id={q["id"][:12]} partição={m.partition} offset={m.offset}')
                    last_message = time.monotonic()
                    if limit and ok + invalid >= limit:
                        break
                if limit and ok + invalid >= limit:
                    break
            if limit and ok + invalid >= limit:
                break
    finally:
        c.close()
        p.close(timeout=15)
        es.close()
    print(f'Consumidos nesta execução: válidos={ok}, DLQ={invalid}')
    if not ok and not invalid:
        print('AVISO: 0 eventos consumidos. Confirme os offsets do grupo e o tópico antes de declarar a A4 concluída.')


def send_invalid(kafka_url: str) -> None:
    p = producer(kafka_url)
    try:
        p.send(TOPICO_DADOS, key=b'teste-invalido', value=b'{json-invalido-para-dlq').get(timeout=45)
        p.flush(timeout=15)
    finally:
        p.close(timeout=15)
    print('Teste de mensagem malformada enviado; rode consumir para validar DLQ.')


def count(url: str, minimum: int = 0) -> None:
    es = elastic(url)
    try:
        if not es.indices.exists(index=INDICE):
            print('Índice ainda não criado')
            return
        total = es.count(index=INDICE)['count']
        print(json.dumps({'indice': INDICE, 'documentos': total}, ensure_ascii=False))
        if total < minimum:
            raise RuntimeError(f'Índice contém {total} documentos; esperado ao menos {minimum}. A4 incompleta.')
    finally:
        es.close()


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('acao', choices=['criar-indice', 'publicar', 'consumir', 'contar', 'verificar', 'enviar-invalido'])
    p.add_argument('--kafka', default='127.0.0.1:29092')
    p.add_argument('--elastic', default='http://127.0.0.1:9200')
    p.add_argument('--arquivo', type=Path, default=ROOT / 'data/extraidos/questoes.jsonl')
    p.add_argument('--limite', type=int, default=0, help='0 = todos; consumidor encerra após 15s sem mensagens')
    p.add_argument('--minimo', type=int, default=1, help='Mínimo de documentos exigido pela ação verificar')
    a = p.parse_args(argv)
    if a.limite < 0:
        p.error('limite não pode ser negativo')
    try:
        if a.acao == 'criar-indice': ensure_index(a.elastic)
        elif a.acao == 'publicar': publish(a.arquivo, a.kafka, a.limite)
        elif a.acao == 'consumir': consume(a.kafka, a.elastic, a.limite)
        elif a.acao == 'contar': count(a.elastic)
        elif a.acao == 'verificar': count(a.elastic, minimum=a.minimo)
        elif a.acao == 'enviar-invalido': send_invalid(a.kafka)
    except Exception as exc:
        print(f'ERRO {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
