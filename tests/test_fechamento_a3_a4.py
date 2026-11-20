import csv
import sys
from pathlib import Path

from scripts.revisar_a3_web import FIELDS, Review
from scripts.reindexar_v2 import completo, quality, preflight


def registro(tipo='objetiva', en='1', alt='1', tp='1'):
    return {'tipo':tipo,'enunciado_correto_1_ou_0':en,
            'alternativas_corretas_1_ou_0':alt,'tipo_correto_1_ou_0':tp}


def test_completo_objetiva():
    assert completo(registro())
    assert not completo(registro(alt=''))


def test_completo_discursiva_nao_exige_alternativas():
    assert completo(registro(tipo='discursiva',alt=''))


def test_status_fiel_a_revisao():
    assert quality(None)=='nao_revisada'
    assert quality(registro(en='',alt='',tp=''))=='nao_revisada'
    assert quality(registro(en='1',alt='',tp=''))=='em_revisao'
    assert quality(registro())=='em_revisao'  # Sem aceite, nao equivale a avaliacao humana
    assert quality(registro(),confirmacao_humana=True)=='aprovada'
    assert quality(registro(alt='0'),confirmacao_humana=True)=='reprovada'
    assert quality(registro(tipo='discursiva',alt=''),confirmacao_humana=True)=='aprovada'


def test_campos_csv_conservados():
    assert FIELDS[0]=='id'
    assert len(FIELDS)==10
