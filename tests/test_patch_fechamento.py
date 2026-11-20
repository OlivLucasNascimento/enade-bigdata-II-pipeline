"""Testes off-line das proteções de proveniência, correções e verificação v2."""
import copy
import csv
import json
from pathlib import Path

from scripts.registrar_midias_a3 import VISUAIS_PRIORITARIAS, remover_artefato_norte
from scripts.reindexar_v2 import (quality, indicativo_ia, completo, validacao_humana,
                                  conferir_ids_e_conteudo, sha, digest_json)


def review_row(**args):
    r = {'tipo': 'objetiva', 'enunciado_correto_1_ou_0': '1',
         'alternativas_corretas_1_ou_0': '1', 'tipo_correto_1_ou_0': '1',
         'observacoes': ''}
    r.update(args)
    return r


def test_revisao_ia_nunca_vira_humana():
    r = review_row(observacoes='Revisão assistida por IA; não é atestação humana')
    assert indicativo_ia(r)
    assert quality(r, confirmacao_humana=True) == 'auditoria_ia'
    assert quality(r) == 'auditoria_ia'


def test_sem_aceite_nao_gera_aprovada():
    assert completo(review_row())
    assert quality(review_row()) == 'em_revisao'
    assert quality(review_row(), confirmacao_humana=True) == 'aprovada'
    assert quality(review_row(alternativas_corretas_1_ou_0='0'), confirmacao_humana=True) == 'reprovada'
    assert quality(review_row(tipo='discursiva', alternativas_corretas_1_ou_0=''), confirmacao_humana=True) == 'aprovada'


def test_aceite_exige_hash_atual_e_50(tmp_path):
    ev = tmp_path / 'evidencias'
    ev.mkdir()
    csvfile = ev / 'A3_revisao_manual.csv'
    rows = [review_row() for _ in range(50)]
    with csvfile.open('w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader(); wr.writerows(rows)
    documento = {'confirmacao_comparacao_pdf': True, 'sha256_csv': sha(csvfile),
                 'responsavel': 'Pessoa conferente', 'quantidade_confirmada': 50}
    (ev / 'A3_aceite_revisao_humana.json').write_text(json.dumps(documento), encoding='utf-8')
    assert validacao_humana(tmp_path, csvfile, rows)
    csvfile.write_text(csvfile.read_text() + '\n')
    assert not validacao_humana(tmp_path, csvfile, rows)


def test_q11_remove_somente_norte_indevido():
    q = {'ano': 2023, 'curso': 'Arquitetura e Urbanismo', 'numero_questao': 11,
         'enunciado': 'N Considerando-se o desenho de uma planta de cobertura com 16 águas...', 'alertas': []}
    assert remover_artefato_norte(q)
    assert q['enunciado'].startswith('Considerando-se')
    assert not remover_artefato_norte(q)
    assert len(VISUAIS_PRIORITARIAS) == 7
    q2 = {'ano': 2023, 'curso': 'Arquitetura e Urbanismo', 'numero_questao': 11,
          'enunciado': 'N\nConsiderando-se o desenho de uma planta de cobertura', 'alertas': []}
    assert remover_artefato_norte(q2)
    outro = copy.deepcopy(q)
    outro['numero_questao'] = 12
    assert not remover_artefato_norte(outro)


class FakeES:
    def __init__(self, documents):
        self.documents = documents

    def mget(self, *, index, body):
        return {'docs': [dict(_id=i, found=i in self.documents,
                              **({'_source': self.documents[i]} if i in self.documents else {}))
                         for i in body['ids']]}


def test_verificacao_detecta_conteudo_antigo_e_id_faltante():
    esperado = [{'id': 'a', 'enunciado': 'novo'}, {'id': 'b', 'enunciado': 'novo'}]
    assert conferir_ids_e_conteudo(FakeES({'a': esperado[0], 'b': esperado[1]}), esperado) == (2, 0, [])
    n, m, divergentes = conferir_ids_e_conteudo(FakeES({'a': {'id': 'a', 'enunciado': 'antigo'}}), esperado)
    assert (n, m, divergentes) == (1, 1, ['a'])
    assert digest_json({'a': 1, 'b': 2}) == digest_json({'b': 2, 'a': 1})
