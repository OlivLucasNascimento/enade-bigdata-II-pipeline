from pathlib import Path
import csv
import hashlib
import json
import fitz
import pytest
from enade_pipeline.extracao import alternativas_do_texto, parse_pdf, extrair_manifesto


def novo_pdf(path: Path):
    d = fitz.open()
    p = d.new_page(width=600, height=850)
    lines = [
        'FORMACAO GERAL',
        'QUESTAO DISCURSIVA 01',
        'Explique a relacao entre acesso a saude e equidade no atendimento publico brasileiro.',
        'QUESTAO 01',
        'Considerando a situacao descrita, assinale a alternativa correta.',
        'A) Primeira alternativa, explicacao completa.',
        'B) Segunda alternativa, explicacao completa.',
        'C) Terceira alternativa, explicacao completa.',
        'D) Quarta alternativa, explicacao completa.',
        'E) Quinta alternativa, explicacao completa.',
        'QUESTIONARIO DE PERCEPCAO DA PROVA',
        'QUESTAO 02',
        'Esta e uma pergunta da pesquisa e nao deve ir para o banco.',
    ]
    for i, line in enumerate(lines):
        p.insert_text((55, 80 + 39 * i), line, fontsize=10)
    d.save(path)
    d.close()


def test_alternativas_sequenciais():
    t = 'Analise as afirmacoes:\nA) Primeiro item\nB) Segundo item\nC) Terceiro item\nD) Quarto item\nE) Quinto item'
    enunciado, alternativas, ok = alternativas_do_texto(t)
    assert ok and enunciado.startswith('Analise')
    assert [a['letra'] for a in alternativas] == list('ABCDE')
    assert alternativas[-1]['texto'] == 'Quinto item'


def test_frase_inicial_nao_e_alternativa():
    enunciado, alternativas, ok = alternativas_do_texto('A fome e um problema\nB Brasil e um pais\nPergunta?')
    assert not ok and not alternativas and 'fome' in enunciado


def test_pagina_originais_discursiva_e_percepcao(tmp_path):
    p = tmp_path / 'prova.pdf'
    novo_pdf(p)
    qs, errors = parse_pdf(p, ano=2023, curso='Enfermagem',
                           pdf_url='https://download.inep.gov.br/prova.pdf', pdf_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    assert len(qs) == 2
    assert [q['tipo_questao'] for q in qs] == ['discursiva', 'objetiva']
    assert qs[0]['numero_questao'] == 1 == qs[1]['numero_questao']
    assert qs[0]['id'] != qs[1]['id']
    assert qs[0]['origem']['pagina_inicial'] == 1
    assert qs[1]['alternativas'][0]['letra'] == 'A'
    assert qs[1]['pendente_revisao'] is True
    assert all('pesquisa' not in q['enunciado'] for q in qs)


def test_execucao_idempotente_arquivo_e_hash(tmp_path):
    (tmp_path / 'data' / 'raw' / '2023').mkdir(parents=True)
    p = tmp_path / 'data' / 'raw' / '2023' / 'prova.pdf'
    novo_pdf(p)
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = tmp_path / 'data' / 'catalogo.csv'
    with manifest.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['arquivo','sha256','status','tipo','ano','curso','url'])
        w.writeheader()
        w.writerow({'arquivo': 'data/raw/2023/prova.pdf', 'sha256': h, 'status': 'existente',
                    'tipo': 'prova', 'ano': 2023, 'curso': 'Enfermagem',
                    'url': 'https://download.inep.gov.br/prova.pdf'})
    a = extrair_manifesto(manifest, tmp_path, tmp_path / 'data' / 'extraidos', 2)
    before = (tmp_path / 'data' / 'extraidos' / 'questoes.jsonl').read_bytes()
    b = extrair_manifesto(manifest, tmp_path, tmp_path / 'data' / 'extraidos', 2)
    after = (tmp_path / 'data' / 'extraidos' / 'questoes.jsonl').read_bytes()
    assert a['questoes_encontradas'] == b['questoes_encontradas'] == 2
    assert before == after


def test_hash_corrompido_e_detectado(tmp_path):
    (tmp_path / 'data' / 'raw').mkdir(parents=True)
    p = tmp_path / 'data' / 'raw' / 'a.pdf'
    novo_pdf(p)
    manifest = tmp_path / 'data' / 'manifesto.csv'
    with manifest.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['arquivo','sha256','status','tipo','ano','curso','url'])
        w.writeheader()
        w.writerow({'arquivo': 'data/raw/a.pdf', 'sha256': 'f'*64,
                    'status': 'baixado', 'tipo': 'prova', 'ano': 2023,
                    'curso': 'Enfermagem', 'url': 'https://download.inep.gov.br/a.pdf'})
    result = extrair_manifesto(manifest, tmp_path, tmp_path / 'data' / 'extraidos')
    assert result['questoes_encontradas'] == 0
    assert 'hash_nao_confere_manifesto' in (tmp_path/'data'/'extraidos'/'pendencias.jsonl').read_text()


def test_bloqueio_travessia_manifesto(tmp_path):
    from enade_pipeline.extracao import pdf_from_manifest
    with pytest.raises(ValueError):
        pdf_from_manifest({'arquivo':'../../etc/passwd'}, tmp_path)


def test_agrupamento_gabarito_2023(tmp_path):
    from enade_pipeline.gabaritos import parse_gabarito
    p = tmp_path / 'gabarito.pdf'
    d = fitz.open()
    pg = d.new_page(width=600, height=850)
    for i, (quest, ans) in enumerate([('QUESTAO DISCURSIVA 1', '***'), ('QUESTAO 1', 'D'),
                                     ('QUESTAO 2', 'B'), ('QUESTAO 3', 'ANULADA'),
                                     ('QUESTAO 4', 'A'), ('QUESTAO 5', 'E')]):
        y = 90 + i * 40
        pg.insert_text((60, y), quest)
        pg.insert_text((440, y), ans)
    d.save(p)
    d.close()
    mapping, alerts = parse_gabarito(p)
    assert mapping[('objetiva', 1)]['valor'] == 'D'
    assert mapping[('objetiva', 3)]['valor'] == 'ANULADA'
    assert mapping[('discursiva', 1)]['valor'] == '***'
    assert not alerts


def test_manifesto_caminhos_portaveis_windows_linux(tmp_path):
    """Regressão: caminhos relativos do CSV sempre funcionam no Windows."""
    from enade_pipeline.extracao import pdf_from_manifest
    expected = tmp_path / 'data' / 'raw' / '2023' / 'prova.pdf'
    for filename in ('data/raw/2023/prova.pdf', r'data\raw\2023\prova.pdf'):
        assert pdf_from_manifest({'arquivo': filename}, tmp_path) == expected


@pytest.mark.parametrize('filename', [
    '../data/raw/prova.pdf', 'data/../segredos.pdf',
    r'C:\Users\Public\segredo.pdf', r'\\servidor\compartilhamento\a.pdf',
    '/etc/passwd', 'data/raw/nao_pdf.txt', '',
])
def test_manifesto_rejeita_caminhos_inseguros(tmp_path, filename):
    from enade_pipeline.extracao import pdf_from_manifest
    with pytest.raises(ValueError):
        pdf_from_manifest({'arquivo': filename}, tmp_path)
