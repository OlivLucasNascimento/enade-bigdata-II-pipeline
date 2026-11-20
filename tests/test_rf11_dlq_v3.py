"""RF11: comportamento unitario da DLQ v3 (sem Docker)."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('enade_v3_dlq', ROOT / 'scripts/indexar_v3.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Ack:
    def get(self, timeout):
        return {'acked': True}


class Producer:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def send(self, topic, key, value):
        self.sent.append((topic, key, json.loads(value)))
        if self.fail:
            return Failure()
        return Ack()


class Failure:
    def get(self, timeout):
        raise TimeoutError('sem ACK da DLQ')


class ES:
    def __init__(self, fail=False):
        self.writes = []
        self.fail = fail

    def index(self, **kwargs):
        if self.fail:
            raise OSError('elasticsearch fora do ar')
        self.writes.append(kwargs)


def event(raw, offset=7):
    return SimpleNamespace(topic='enade.questoes.v3', partition=1, offset=offset, value=raw)


def valid():
    return {
        'id': hashlib.sha256(b'caso-rf11').hexdigest(),
        'ano': 2021, 'area': 'Computacao', 'curso': 'Curso sintentico',
        'tipo_formacao': 'CE', 'numero_questao': 3, 'tipo_questao': 'objetiva',
        'enunciado': 'Enunciado de teste', 'alternativas': [],
        'pendente_revisao': True, 'status_validacao': 'nao_revisada',
        'revisado_humanamente': False,
        'origem': {'pdf_url': 'https://example.org/nao-real.pdf', 'pdf_sha256': 'a'*64,
                   'pagina_inicial': 1, 'pagina_final': 1}
    }


def test_json_invalido_vai_dlq_com_payload_e_offset():
    raw = b'{json-com-erro'
    p, es, committed = Producer(), ES(), []
    assert module.process_message(event(raw), es=es, dlq_producer=p,
                                  commit_offset=committed.append) == 'dlq'
    assert len(p.sent) == 1 and not es.writes
    topic, key, msg = p.sent[0]
    assert topic == module.DLQ_TOPIC
    assert key.decode() == msg['evento_sha256'] == hashlib.sha256(raw).hexdigest()
    assert base64.b64decode(msg['evento_base64']) == raw
    assert msg['origem'] == {'topico': 'enade.questoes.v3', 'particao': 1, 'offset': 7}
    assert committed and committed[0].offset == 7


def test_schema_invalido_vai_dlq_e_evento_valido_continua():
    p, es, committed = Producer(), ES(), []
    assert module.process_message(event(b'{}'), es=es, dlq_producer=p,
                                  commit_offset=committed.append) == 'dlq'
    obj = valid()
    assert module.process_message(event(json.dumps(obj).encode(), 8), es=es,
                                  dlq_producer=p, commit_offset=committed.append) == 'indexado'
    assert len(p.sent) == 1 and len(es.writes) == 1
    assert es.writes[0]['index'] == module.INDEX
    assert [e.offset for e in committed] == [7, 8]


def test_sem_ack_dlq_nao_confirma_offset():
    p, es, committed = Producer(fail=True), ES(), []
    with pytest.raises(TimeoutError):
        module.process_message(event(b'{bad'), es=es, dlq_producer=p,
                               commit_offset=committed.append)
    assert not committed and not es.writes


def test_falha_elasticsearch_nao_vai_dlq_nem_confirma_offset():
    p, es, committed = Producer(), ES(fail=True), []
    with pytest.raises(OSError):
        module.process_message(event(json.dumps(valid()).encode()), es=es,
                               dlq_producer=p, commit_offset=committed.append)
    assert not committed and not p.sent


def test_classificacao_sem_rascunho_vai_dlq():
    obj = valid()
    obj['status_validacao'] = 'aprovada'
    p, es, committed = Producer(), ES(), []
    assert module.process_message(event(json.dumps(obj).encode()), es=es,
                                  dlq_producer=p, commit_offset=committed.append) == 'dlq'
    assert len(p.sent) == 1 and not es.writes


def test_commit_falhou_nao_e_ignorado():
    p, es = Producer(), ES()
    def failing_commit(event):
        raise OSError('falha ao confirmar offset')
    with pytest.raises(OSError):
        module.process_message(event(b'{}'), es=es, dlq_producer=p,
                               commit_offset=failing_commit)
    assert len(p.sent) == 1
