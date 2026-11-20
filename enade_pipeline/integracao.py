"""Contrato de dados e mapping compartilhado com a futura API do integrante 2."""
from __future__ import annotations

import hashlib
import json
from urllib.parse import urlparse

from enade_pipeline.higienizacao import contar_marcas

INDICE = 'enade-questoes-v1'
TOPICO_DADOS = 'enade.questoes'
TOPICO_ERRO = 'enade.dlq'

MAPPING = {
    'settings': {'number_of_shards': 1, 'number_of_replicas': 0},
    'mappings': {
        'dynamic': False,
        'properties': {
            'id': {'type': 'keyword'}, 'ano': {'type': 'integer'},
            'area': {'type': 'keyword', 'fields': {'texto': {'type': 'text', 'analyzer': 'brazilian'}}},
            'curso': {'type': 'keyword', 'fields': {'texto': {'type': 'text', 'analyzer': 'brazilian'}}},
            'tipo_formacao': {'type': 'keyword'}, 'origem_tipo_formacao': {'type': 'keyword'},
            'numero_questao': {'type': 'integer'}, 'tipo_questao': {'type': 'keyword'},
            'texto_base': {'type': 'text', 'analyzer': 'brazilian'},
            'enunciado': {'type': 'text', 'analyzer': 'brazilian'},
            'alternativas': {'properties': {'letra': {'type': 'keyword'},
                                          'texto': {'type': 'text', 'analyzer': 'brazilian'}}},
            'gabarito': {'type': 'keyword'}, 'anulada': {'type': 'boolean'},
            'competencias': {'type': 'keyword'}, 'objetos_conhecimento': {'type': 'keyword'},
            'pendente_revisao': {'type': 'boolean'}, 'alertas': {'type': 'keyword'},
            'midias': {'properties': {'tipo': {'type': 'keyword'}, 'pagina': {'type': 'integer'},
                                      'descricao': {'type': 'text', 'analyzer': 'brazilian'},
                                      'conversao': {'type': 'keyword'}}},
            'origem': {'properties': {'pdf_url': {'type': 'keyword'}, 'pdf_sha256': {'type': 'keyword'},
                                      'pagina_inicial': {'type': 'integer'},
                                      'pagina_final': {'type': 'integer'},
                                      'gabarito_pdf_url': {'type': 'keyword'},
                                      'gabarito_pdf_sha256': {'type': 'keyword'},
                                      'gabarito_pagina': {'type': 'integer'}}}
        }
    }
}


def validar_questao(q: object) -> dict:
    """Validação segura antes de publicar/indexar. A revisão editorial é separada."""
    if not isinstance(q, dict):
        raise ValueError('evento deve ser objeto JSON')
    fields = ['id', 'ano', 'area', 'curso', 'tipo_formacao', 'numero_questao', 'tipo_questao',
              'enunciado', 'alternativas', 'pendente_revisao', 'origem']
    missing = [f for f in fields if f not in q]
    if missing:
        raise ValueError('campos ausentes: ' + ', '.join(missing))
    if not isinstance(q['id'], str) or len(q['id']) != 64 or any(c not in '0123456789abcdef' for c in q['id'].lower()):
        raise ValueError('id deve ser sha256 em hexadecimal')
    if type(q['ano']) is not int or not 2004 <= q['ano'] <= 2100:
        raise ValueError('ano inválido')
    if type(q['numero_questao']) is not int or not 1 <= q['numero_questao'] <= 99:
        raise ValueError('número da questão inválido')
    for k in ['area', 'curso', 'enunciado']:
        if not isinstance(q[k], str) or not q[k].strip():
            raise ValueError(f'{k} obrigatório')
    if q['tipo_questao'] not in ('objetiva', 'discursiva'):
        raise ValueError('tipo_questao inválido')
    if q['tipo_formacao'] not in ('FG', 'CE', 'nao_identificado'):
        raise ValueError('tipo_formacao inválido')
    if not isinstance(q['alternativas'], list):
        raise ValueError('alternativas deve ser lista')
    if contar_marcas(q) > 0:
        raise ValueError('marca VALIDINEP2023 presente: reextraia e revise a A3 antes de publicar')
    if not isinstance(q['pendente_revisao'], bool):
        raise ValueError('pendente_revisao deve ser booleano')
    for alt in q['alternativas']:
        if not isinstance(alt, dict) or not isinstance(alt.get('letra'), str) or alt['letra'] not in 'ABCDE' or not isinstance(alt.get('texto'), str):
            raise ValueError('alternativa malformada')
    src = q['origem']
    if not isinstance(src, dict):
        raise ValueError('origem obrigatória')
    url = src.get('pdf_url')
    if not isinstance(url, str) or urlparse(url).scheme not in ('http', 'https'):
        raise ValueError('url de origem inválida')
    if not isinstance(src.get('pdf_sha256'), str) or len(src['pdf_sha256']) != 64:
        raise ValueError('hash de origem ausente')
    a, b = src.get('pagina_inicial'), src.get('pagina_final')
    if type(a) is not int or type(b) is not int or a < 1 or b < a:
        raise ValueError('páginas da origem inválidas')
    return q


def fingerprint(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(q: dict) -> bytes:
    return json.dumps(q, ensure_ascii=False, sort_keys=True).encode('utf-8')
