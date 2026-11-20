#!/usr/bin/env python3
"""Kafka -> Elasticsearch v2 com auditoria verificável e modo RASCUNHO.

NUNCA atesta que uma revisão feita por IA é revisão humana. Não toca no v1.
Laboratório local (Kafka PLAINTEXT e Elasticsearch HTTP), não satisfaz Kerberos.
"""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enade_pipeline.integracao import MAPPING, validar_questao, encode

TOPIC = 'enade.questoes.v2'
INDEX = 'enade-questoes-v2'
GROUP = 'enade-indexador-v2'
FIELDS = ['enunciado_correto_1_ou_0', 'alternativas_corretas_1_ou_0', 'tipo_correto_1_ou_0']
MARCA_IA = ('assistida por ia', 'assistido por ia', 'auditoria por ia', 'revisão por ia')


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def digest_json(data: dict) -> str:
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def completo(row: dict) -> bool:
    return (row.get(FIELDS[0]) in ('0', '1') and row.get(FIELDS[2]) in ('0', '1')
            and (row.get('tipo') == 'discursiva' or row.get(FIELDS[1]) in ('0', '1')))


def indicativo_ia(row: dict) -> bool:
    nota = (row.get('observacoes') or '').lower()
    return any(x in nota for x in MARCA_IA)


def quality(row: dict | None, *, confirmacao_humana: bool = False) -> str:
    if row is None:
        return 'nao_revisada'
    if indicativo_ia(row):
        return 'auditoria_ia'
    if completo(row) and confirmacao_humana:
        campos = [FIELDS[0], FIELDS[2]] if row['tipo'] == 'discursiva' else FIELDS
        return 'aprovada' if all(row[c] == '1' for c in campos) else 'reprovada'
    return 'em_revisao' if any(row.get(c) in ('0', '1') for c in FIELDS) else 'nao_revisada'


def validacao_humana(base: Path, csvfile: Path, rows: list[dict]) -> bool:
    """Exige confirmação explícita e vinculada ao SHA-256 exato do CSV."""
    p = base / 'evidencias/A3_aceite_revisao_humana.json'
    if not p.is_file():
        return False
    try:
        d = json.loads(p.read_text(encoding='utf-8-sig'))
        return (d.get('confirmacao_comparacao_pdf') is True
                and d.get('sha256_csv') == sha(csvfile)
                and isinstance(d.get('responsavel'), str) and bool(d['responsavel'].strip())
                and d.get('quantidade_confirmada') == 50
                and len(rows) == 50 and all(completo(r) and not indicativo_ia(r) for r in rows))
    except (ValueError, OSError, TypeError):
        return False


def source(base: Path):
    origem = base / 'data/extraidos/questoes_com_midias.jsonl'
    if not origem.is_file():
        raise FileNotFoundError('Falta questoes_com_midias.jsonl: execute registrar_midias_a3.py')
    qs = [json.loads(line) for line in origem.read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(qs) != 80 or len({q['id'] for q in qs}) != 80:
        raise ValueError(f'Esperados 80 IDs únicos do piloto: encontrados {len(qs)}')
    csvfile = base / 'evidencias/A3_revisao_manual.csv'
    with csvfile.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 50 or len({r['id'] for r in rows}) != 50:
        raise ValueError('Esperados 50 IDs distintos no CSV de revisão')
    ref = {r['id']: r for r in rows}
    if not set(ref).issubset({q['id'] for q in qs}):
        raise ValueError('O CSV da revisão não corresponde aos IDs do JSONL atual')
    confirmada = validacao_humana(base, csvfile, rows)
    converted = []
    for q in qs:
        z = copy.deepcopy(q)
        row = ref.get(z['id'])
        status = quality(row, confirmacao_humana=confirmada)
        z['status_validacao'] = status
        z['origem_avaliacao'] = ('ia_assistida' if row is not None and indicativo_ia(row)
                                else 'humana_confirmada' if confirmada and row is not None
                                else 'nao_confirmada')
        z['revisado_humanamente'] = status in ('aprovada', 'reprovada')
        z['pendente_revisao'] = status != 'aprovada'
        z['alertas'] = list(z.get('alertas') or [])
        if status != 'aprovada' and 'pendente_validacao_editorial' not in z['alertas']:
            z['alertas'].append('pendente_validacao_editorial')
        validar_questao(z)
        converted.append(z)
    return converted, rows, origem, csvfile, confirmada


def preflight(base: Path, require_review: bool = True):
    qs, rows, origem, csvfile, confirmada = source(base)
    reviewed = sum(completo(r) and not indicativo_ia(r) for r in rows)
    s = Counter(q['status_validacao'] for q in qs)
    report = {
        'total': len(qs), 'amostra': len(rows),
        'avaliacoes_preenchidas_nao_ia': reviewed,
        'avaliacoes_assistidas_ia': sum(indicativo_ia(r) for r in rows),
        'confirmacao_humana_valida': confirmada,
        'status_validacao': dict(s), 'arquivo_questoes_sha256': sha(origem),
        'arquivo_revisao_sha256': sha(csvfile), 'indice_planejado': INDEX,
        'topico_planejado': TOPIC,
        'atencao': '50 registros de IA não equivalem a 50 revisões humanas. Modo rascunho não aprova questões.'
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if require_review and not confirmada:
        raise ValueError('PUBLICAÇÃO FINAL BLOQUEADA: faltam 50 conferências humanas e aceite vinculado ao CSV. '
                         'Para um teste de indexação identificado como rascunho, use --modo-rascunho.')
    return qs, report


def kafka_producer(bootstrap: str):
    from kafka import KafkaProducer
    return KafkaProducer(bootstrap_servers=bootstrap, acks='all', retries=4,
                         max_in_flight_requests_per_connection=1, request_timeout_ms=30000)


def es_client(url: str):
    from elasticsearch import Elasticsearch
    e = Elasticsearch(url, request_timeout=25, max_retries=3, retry_on_timeout=True)
    if not e.ping():
        raise RuntimeError('Elasticsearch indisponível')
    return e


def setup(kafka: str, elastic: str):
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError
    admin = KafkaAdminClient(bootstrap_servers=kafka, client_id='enade-v2-setup', request_timeout_ms=30000)
    try:
        try:
            admin.create_topics([NewTopic(name=TOPIC, num_partitions=3, replication_factor=1)])
        except TopicAlreadyExistsError:
            pass
    finally:
        admin.close()
    es = es_client(elastic)
    try:
        if not es.indices.exists(index=INDEX):
            mapping = copy.deepcopy(MAPPING)
            mapping['mappings']['properties'].update({
                'status_validacao': {'type': 'keyword'},
                'revisado_humanamente': {'type': 'boolean'},
                'origem_avaliacao': {'type': 'keyword'},
            })
            es.indices.create(index=INDEX, body=mapping)
            print('Índice criado:', INDEX)
        else:
            print('Índice existente (não apagado):', INDEX)
    finally:
        es.close()


def publish(kafka: str, items: list[dict]):
    prod = kafka_producer(kafka)
    try:
        for q in items:
            prod.send(TOPIC, key=q['id'].encode('ascii'), value=encode(q)).get(timeout=45)
        prod.flush(timeout=30)
    finally:
        prod.close(timeout=15)
    print(f'Publicados com ACK: {len(items)} mensagens em {TOPIC}')


def conferir_ids_e_conteudo(es, items: list[dict]):
    """Comparação do conteúdo armazenado, não apenas _count: detecta v2 desatualizado."""
    wanted = {q['id']: digest_json(q) for q in items}
    response = es.mget(index=INDEX, body={'ids': list(wanted)})
    found, outdated = set(), []
    for doc in response['docs']:
        id_ = doc['_id']
        if doc.get('found'):
            found.add(id_)
            if digest_json(doc['_source']) != wanted[id_]:
                outdated.append(id_)
    return len(found), len(wanted) - len(found), outdated


def consume(kafka: str, elastic: str, items: list[dict], timeout: int = 60):
    from kafka import KafkaConsumer, TopicPartition
    from kafka.structs import OffsetAndMetadata
    c = KafkaConsumer(TOPIC, bootstrap_servers=kafka, group_id=GROUP,
                      enable_auto_commit=False, auto_offset_reset='earliest', max_poll_records=100)
    e = es_client(elastic)
    received = 0
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            batches = c.poll(timeout_ms=1000, max_records=100)
            if not batches:
                present, missing, outdated = conferir_ids_e_conteudo(e, items)
                if missing == 0 and not outdated:
                    break
                continue
            for tp, msgs in batches.items():
                for event in msgs:
                    # Se falhar, NÃO confirma offset. Próxima tentativa reprocessa mesmo ID.
                    q = validar_questao(json.loads(event.value.decode('utf-8')))
                    if q.get('status_validacao') not in ('aprovada', 'reprovada', 'nao_revisada', 'em_revisao', 'auditoria_ia'):
                        raise ValueError('status_validacao ausente ou inválido no evento')
                    e.index(index=INDEX, id=q['id'], document=q)
                    c.commit(offsets={TopicPartition(event.topic, event.partition):
                                      OffsetAndMetadata(event.offset + 1, '', -1)})
                    received += 1
        e.indices.refresh(index=INDEX)
        present, missing, outdated = conferir_ids_e_conteudo(e, items)
        print(f'Processados nesta execução: {received}; IDs presentes: {present}; faltantes: {missing}; divergentes: {len(outdated)}')
        if missing or outdated:
            raise RuntimeError('Indexação incompleta/desatualizada: verifique conexão, tempo limite e offsets do grupo')
    finally:
        c.close()
        e.close()
    return received


def verify(base: Path, url: str, items: list[dict], *, modo_rascunho: bool):
    es = es_client(url)
    try:
        es.indices.refresh(index=INDEX)
        count = es.count(index=INDEX)['count']
        present, missing, outdated = conferir_ids_e_conteudo(es, items)
        s = Counter(q['status_validacao'] for q in items)
        report = {
            'indice': INDEX, 'contagem_elasticsearch': count, 'esperados': len(items),
            'ids_presentes': present, 'ids_faltantes': missing,
            'ids_com_conteudo_divergente': outdated[:20],
            'status_previstos': dict(s),
            'modo_rascunho': modo_rascunho, 'seguranca': 'LABORATORIO_SEM_KERBEROS',
            'aprovado_tecnicamente': (count == len(items) and missing == 0 and not outdated),
            'aviso': 'A indexação técnica não certifica qualidade editorial ou aprovação humana.'
        }
        ev = base / 'evidencias'
        ev.mkdir(exist_ok=True)
        (ev / 'A4_v2_verificacao.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not report['aprovado_tecnicamente']:
            raise RuntimeError('Verificação da v2 falhou: contagem/IDs/conteúdo não correspondem à fonte')
    finally:
        es.close()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('acao', choices=['diagnostico', 'executar', 'verificar'])
    p.add_argument('--base', type=Path, default=ROOT)
    p.add_argument('--kafka', default='127.0.0.1:29092')
    p.add_argument('--elastic', default='http://127.0.0.1:9200')
    p.add_argument('--modo-rascunho', action='store_true',
                   help='Permite indexar para TESTES sem afirmar revisão humana concluída')
    args = p.parse_args(argv)
    base = args.base.resolve()
    try:
        if args.acao == 'diagnostico':
            preflight(base, require_review=False)
            return 0
        items, _ = preflight(base, require_review=not args.modo_rascunho)
        if args.acao == 'executar':
            setup(args.kafka, args.elastic)
            publish(args.kafka, items)
            consume(args.kafka, args.elastic, items)
        verify(base, args.elastic, items, modo_rascunho=args.modo_rascunho)
        return 0
    except Exception as e:
        print(f'ERRO {type(e).__name__}: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
