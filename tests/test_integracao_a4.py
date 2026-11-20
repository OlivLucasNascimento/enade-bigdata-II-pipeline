import hashlib
import json
from enade_pipeline.integracao import validar_questao, MAPPING, encode, fingerprint


def sample():
    return {'id':'a'*64, 'ano': 2023, 'area':'Enfermagem','curso':'Enfermagem',
            'numero_questao': 1, 'tipo_formacao':'FG','tipo_questao':'objetiva',
            'enunciado':'Texto completo da questão.', 'alternativas':[{'letra':'A','texto':'Sim.'}],
            'pendente_revisao': True, 'origem': {'pdf_url':'https://download.inep.gov.br/x.pdf',
                                                'pdf_sha256':'b'*64,'pagina_inicial':2,'pagina_final':3}}


def test_valida_amostra():
    q = sample()
    assert validar_questao(q) is q
    assert json.loads(encode(q)) == q


def test_rejeita_json_malformado():
    try:
        validar_questao({'id':'qualquer'})
    except ValueError as e:
        assert 'campos ausentes' in str(e)
    else:
        raise AssertionError('Mensagem inválida foi aceita')


def test_rejeita_paginas_incoerentes():
    q = sample()
    q['origem']['pagina_final'] = 1
    try: validar_questao(q)
    except ValueError as e: assert 'páginas' in str(e)
    else: raise AssertionError('Páginas incoerentes foram aceitas')


def test_idempotencia_do_documento():
    q = sample()
    key1 = (q['id'], fingerprint(encode(q)))
    key2 = (q['id'], fingerprint(encode(q)))
    assert key1 == key2
    assert MAPPING['settings']['number_of_replicas'] == 0
    assert MAPPING['mappings']['properties']['enunciado']['type'] == 'text'
