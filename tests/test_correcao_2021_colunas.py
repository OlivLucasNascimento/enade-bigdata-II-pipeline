import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/corrigir_7_questoes_2021.py'
SPEC = importlib.util.spec_from_file_location('corrigir_7_questoes_2021', SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


@pytest.mark.parametrize('titulo', ['QUESTÃO 09', 'QuEStãO 31', 'QUESTÃO 26'])
def test_ordem_leitura_e_alternativas_completas(titulo):
    numero = int(titulo.split()[-1])
    source = '\n'.join([
        '19', 'CIÊNCIA DA COMPUTAÇÃO', titulo,
        'Enunciado longo do material oficial, mantido dentro da coluna esquerda, ' * 2,
        'A\t Primeira alternativa completa.',
        'B\t Segunda alternativa continua', 'na linha seguinte.',
        'C  Terceira alternativa completa.',
        'D\t Quarta alternativa completa.',
        'E  Quinta alternativa completa.',
        'Área livre', f'QUESTÃO {numero+1:02}',
        'O conteudo da coluna direita NAO PODE aparecer no enunciado.',
    ])
    body, opts = mod.extrair_questao(source, numero)
    assert 'coluna esquerda' in body
    assert 'coluna direita' not in body
    assert [x['letra'] for x in opts] == list('ABCDE')
    assert opts[1]['texto'].endswith('na linha seguinte.')


def test_alternativas_incompletas_bloqueadas():
    bad = 'QUESTÃO 11\n' + 'Um enunciado completo e longo. '*7 + '\nA\tSim\nB\tNao'
    with pytest.raises(ValueError, match='alternativas incompletas'):
        mod.extrair_questao(bad, 11)


def test_nao_aceita_questao_inexistente():
    with pytest.raises(ValueError, match='Cabecalho'):
        mod.extrair_questao('QUESTÃO 10\ntexto', 9)
