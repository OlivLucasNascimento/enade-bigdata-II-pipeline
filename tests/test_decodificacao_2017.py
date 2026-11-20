"""Regressoes para a fonte com mapeamento Unicode defeituoso do ENADE 2017."""
from pathlib import Path
import fitz
from enade_pipeline.decodificacao_2017 import decodificar_span, KNOWN_HASHES_2017
from enade_pipeline.extracao import alternativas_do_texto
from enade_pipeline.gabaritos import parse_gabarito


def test_cabecalho_corrompido_2017():
    assert decodificar_span('Yh\x1c^d\x08K\x03Ϭϰ\x03', 'Calibri-Bold').strip() == 'QUESTÃO 04'
    assert decodificar_span('^ŽďƌĞ\x03Ă\x03ƚĞůĞǀŝƐĆŽ', 'Calibri') == 'Sobre a televisão'


def test_leitura_comum_nao_deve_ser_corrompida():
    assert decodificar_span('QUESTÃO 04', 'Calibri-Bold') == 'QUESTÃO 04'
    assert decodificar_span('QUESTIONÁRIO DE PERCEPÇÃO DA PROVA', 'Calibri') == 'QUESTIONÁRIO DE PERCEPÇÃO DA PROVA'
    assert decodificar_span('Δ = 2', 'Euclid') == 'Δ = 2'
    assert len(KNOWN_HASHES_2017) == 2


def test_alternativas_em_linhas_minusculas_2017():
    text = 'Questão sobre televisão\nA contemplação crítica\nB fragmentação das notícias\nC especialização do conhecimento\nD atenção concentrada\nE reflexão crítica'
    corpo, opcoes, valido = alternativas_do_texto(text, modo_2017=True)
    assert valido and corpo == 'Questão sobre televisão'
    assert [a['letra'] for a in opcoes] == list('ABCDE')


def make_gabarito(tmp_path, n=35, answer_override=None):
    pdf = fitz.open()
    pagina = pdf.new_page()
    entries = [(i, 'ABCDE'[(i-1) % 5]) for i in range(1, n+1)]
    if answer_override:
        entries = answer_override
    texto = 'GABARITO DEFINITIVO DAS QUESTÕES DE MÚLTIPLA ESCOLHA\nITEM GABARITO\n' + '\n'.join(f'{num}      {letra}' for num, letra in entries)
    pagina.insert_textbox(fitz.Rect(40, 40, 550, 780), texto, fontname='helv', fontsize=10)
    target = tmp_path / 'gabarito.pdf'
    pdf.save(target)
    pdf.close()
    return target


def test_gabarito_2017_35_itens(tmp_path):
    outcome, errors = parse_gabarito(make_gabarito(tmp_path))
    assert errors == []
    assert len(outcome) == 35
    assert outcome[('objetiva', 35)]['valor'] == 'E'


def test_gabarito_2017_incompleto_nao_vincular(tmp_path):
    outcome, errors = parse_gabarito(make_gabarito(tmp_path, n=34))
    assert outcome == {}
    assert errors and '35' in errors[0]
