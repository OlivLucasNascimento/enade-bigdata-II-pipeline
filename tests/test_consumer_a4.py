"""Testes determinísticos, sem Docker, da espera pela atribuição e validação final."""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def load_cli():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('pipeline_a4_test', root / 'scripts' / 'pipeline_a4.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def questao():
    return {
        'id': 'a' * 64, 'ano': 2023, 'area': 'Enfermagem', 'curso': 'Enfermagem',
        'numero_questao': 1, 'tipo_formacao': 'FG', 'tipo_questao': 'objetiva',
        'enunciado': 'Questão fictícia válida para o teste.', 'alternativas': [],
        'pendente_revisao': True,
        'origem': {'pdf_url': 'https://download.inep.gov.br/prova.pdf',
                   'pdf_sha256': 'b' * 64, 'pagina_inicial': 2, 'pagina_final': 2}
    }


def test_consumer_aguarda_atribuicao_antes_de_concluir(monkeypatch):
    cli = load_cli()
    qt = questao()

    class TP:
        def __init__(self, topic, partition):
            self.topic, self.partition = topic, partition
        def __hash__(self):
            return hash((self.topic, self.partition))
        def __eq__(self, other):
            return isinstance(other, TP) and (self.topic, self.partition) == (other.topic, other.partition)

    class Msg:
        topic = 'enade.questoes'
        partition = 0
        offset = 7
        value = json.dumps(qt).encode('utf-8')

    instance = {}

    class FakeConsumer:
        def __init__(self, *args, **kwargs):
            self.calls = 0
            self.commits = []
            instance['consumer'] = self
        def poll(self, **kwargs):
            self.calls += 1
            return {TP('enade.questoes', 0): [Msg()]} if self.calls == 3 else {}
        def assignment(self):
            return {TP('enade.questoes', 0)} if self.calls >= 2 else set()
        def position(self, tp):
            return 7
        def end_offsets(self, tps):
            return {tps[0]: 8}
        def commit(self, offsets):
            self.commits.append(offsets)
        def close(self):
            pass

    class FakeProducer:
        def close(self, **kwargs):
            pass

    class FakeES:
        def __init__(self):
            self.indexed = []
            self.indices = types.SimpleNamespace(exists=lambda index: True)
        def index(self, **kwargs):
            self.indexed.append(kwargs)
        def close(self):
            pass

    es = FakeES()
    monkeypatch.setattr(cli, 'elastic', lambda url: es)
    monkeypatch.setattr(cli, 'producer', lambda url: FakeProducer())
    monkeypatch.setitem(sys.modules, 'kafka', types.SimpleNamespace(
        KafkaConsumer=FakeConsumer, TopicPartition=TP,
        OffsetAndMetadata=lambda *args: args
    ))
    cli.consume('localhost:29092', 'http://localhost:9200', limit=1)
    assert instance['consumer'].calls == 3
    assert len(instance['consumer'].commits) == 1
    assert len(es.indexed) == 1
    assert es.indexed[0]['id'] == qt['id']


def test_verificar_rejeita_indice_vazio(monkeypatch):
    cli = load_cli()
    class FakeES:
        indices = types.SimpleNamespace(exists=lambda index: True)
        def count(self, **kwargs):
            return {'count': 0}
        def close(self):
            pass
    monkeypatch.setattr(cli, 'elastic', lambda _: FakeES())
    with pytest.raises(RuntimeError, match='0 documentos'):
        cli.count('http://localhost:9200', minimum=1)
