from copy import deepcopy
from enade_pipeline.higienizacao import contar_marcas, higienizar_questao
from enade_pipeline.integracao import validar_questao
import pytest


def amostra():
    return {
        'id':'a'*64, 'ano':2023,'curso':'Agronomia','area':'Agronomia',
        'numero_questao':2,'tipo_questao':'objetiva','tipo_formacao':'FG',
        'enunciado':'Enunciado correto da questão sem marca indevida.',
        'alternativas':[{'letra':'A','texto':'Válido.'},
                        {'letra':'E','texto':'Resposta E. VALIDINEP2023VALIDIN3P2023'}],
        'texto_base': None, 'alertas': [], 'pendente_revisao': True,
        'origem':{'pdf_url':'https://download.inep.gov.br/enade/teste.pdf',
                  'pdf_sha256':'b'*64,'pagina_inicial':4,'pagina_final':4}
    }


def test_remove_marcas_preserva_bruto_e_rastreabilidade():
    original = amostra()
    snapshot = deepcopy(original)
    limpa, log = higienizar_questao(original)
    assert original == snapshot
    assert original['alternativas'][1]['texto'].endswith('VALIDINEP2023VALIDIN3P2023')
    assert limpa['alternativas'][1]['texto'] == 'Resposta E. '
    assert limpa['id'] == original['id']
    assert limpa['origem'] == original['origem']
    assert log['marcas_removidas'] == 2
    assert log['campos_atingidos'] == {'alternativas[1].texto':2}
    assert limpa['pendente_revisao'] is True
    assert 'marca_validinep_removida_revisar' in limpa['alertas']


def test_sem_marca_preserva_questao():
    q = amostra()
    q['alternativas'][1]['texto'] = 'Texto original.'
    limpa, log = higienizar_questao(q)
    assert limpa == q
    assert log is None


def test_reexecucao_nao_altera_novamente():
    limpa, _ = higienizar_questao(amostra())
    segunda, log = higienizar_questao(limpa)
    assert log is None
    assert segunda == limpa
    assert contar_marcas(segunda) == 0


def test_bloqueia_publicacao_contaminada():
    with pytest.raises(ValueError, match='VALIDINEP2023'):
        validar_questao(amostra())
    limpa, _ = higienizar_questao(amostra())
    assert validar_questao(limpa) is limpa


def test_reextracao_gera_bruto_limpo_e_auditoria(tmp_path):
    import csv
    import hashlib
    import json
    import fitz
    from enade_pipeline.extracao import extrair_manifesto

    arquivo = tmp_path / 'data' / 'raw' / '2023' / 'prova.pdf'
    arquivo.parent.mkdir(parents=True)
    doc = fitz.open()
    page = doc.new_page(width=600, height=850)
    linhas = [
        'QUESTAO 01',
        'Qual alternativa representa a situacao correta de teste da prova?',
        'A) Primeiro enunciado.',
        'B) Segundo enunciado.',
        'C) Terceiro enunciado.',
        'D) Quarto enunciado.',
        'E) Quinto enunciado. VALIDINEP2023VALIDIN3P2023',
    ]
    for i, linha in enumerate(linhas):
        page.insert_text((55, 100 + 35 * i), linha, fontsize=10)
    doc.save(arquivo)
    doc.close()

    manifesto = tmp_path / 'data' / 'catalogo.csv'
    with manifesto.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['arquivo', 'sha256', 'status', 'tipo', 'ano', 'curso', 'url'])
        writer.writeheader()
        writer.writerow({
            'arquivo': 'data/raw/2023/prova.pdf', 'sha256': hashlib.sha256(arquivo.read_bytes()).hexdigest(),
            'status': 'baixado', 'tipo': 'prova', 'ano': 2023, 'curso': 'Teste',
            'url': 'https://download.inep.gov.br/enade/2023_teste.pdf'
        })

    saida = tmp_path / 'data' / 'extraidos'
    resumo = extrair_manifesto(manifesto, tmp_path, saida, 2)
    assert resumo['questoes_encontradas'] == 1
    assert resumo['questoes_com_marca'] == 1
    assert resumo['marcas_removidas'] == 2
    assert resumo['marcas_residuais'] == 0
    bruto = json.loads((saida / 'questoes_brutas.jsonl').read_text(encoding='utf-8').splitlines()[0])
    limpo = json.loads((saida / 'questoes.jsonl').read_text(encoding='utf-8').splitlines()[0])
    auditoria = json.loads((saida / 'auditoria_marcas.jsonl').read_text(encoding='utf-8').splitlines()[0])
    assert bruto['id'] == limpo['id'] == auditoria['id']
    assert contar_marcas(bruto) == 2
    assert contar_marcas(limpo) == 0
    assert limpo['pendente_revisao'] is True
