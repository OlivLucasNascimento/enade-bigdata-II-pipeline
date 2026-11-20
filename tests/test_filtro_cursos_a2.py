import importlib.util
import sys
import types
from pathlib import Path


def carregar():
    if 'truststore' not in sys.modules:
        sys.modules['truststore'] = types.SimpleNamespace(inject_into_ssl=lambda: None)
    caminho = Path(__file__).resolve().parents[1] / 'scripts' / 'coletar_enade.py'
    spec = importlib.util.spec_from_file_location('coletar_enade_filtro_cursos', caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_filtro_nome_acentuado_e_modalidade():
    m = carregar()
    itens = [
        {'curso':'Ciência da Computação – Bacharelado'},
        {'curso':'Ciência da Computação (Licenciatura)'},
        {'curso':'Sistemas de Informação (Bacharelado)'},
        {'curso':'Engenharia de Computação'},
        {'curso':'Tecnologia em Redes de Computadores'},
        {'curso':'nao_identificado'},
    ]
    resultado = m.filtrar_por_curso(itens, ['ciencia da computacao', 'Sistemas de Informação'])
    assert len(resultado) == 3
    assert [x['curso'] for x in resultado] == [x['curso'] for x in itens[:3]]


def test_sem_filtro_nao_modifica_lista():
    m = carregar()
    itens = [{'curso': 'Agronomia'}]
    assert m.filtrar_por_curso(itens, []) == itens


def test_parse_argumentos_cursos():
    m = carregar()
    args = m.parse_args(['--anos', '2017,2021', '--cursos', 'Ciência da Computação,Sistemas de Informação',
                         '--somente-pendentes', '--listar-selecao'])
    assert args.years == [2017, 2021]
    assert args.cursos_filtro == ['Ciência da Computação', 'Sistemas de Informação']
    assert args.listar_selecao
