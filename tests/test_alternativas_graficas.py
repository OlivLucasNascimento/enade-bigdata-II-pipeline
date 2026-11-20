import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'completar_alternativas_visuais.py'
spec = importlib.util.spec_from_file_location('completar_alternativas_visuais', PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_10_recortes_mapeados_sem_duplicar_letras():
    assert set(mod.RECORTES) == {('Arquitetura e Urbanismo', 11), ('Arquitetura e Urbanismo', 16)}
    for item in mod.RECORTES.values():
        assert set(item['retangulos']) == set('ABCDE')
        assert len(set(tuple(v) for v in item['retangulos'].values())) == 5


def test_outros_itens_nao_sao_modificados(tmp_path):
    q = {'ano': 2023, 'curso': 'Agronomia', 'numero_questao': 11}
    assert mod.completar(q, base=tmp_path, pdf_path=tmp_path / 'nao_existe.pdf') == (q, 0)
