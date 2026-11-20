"""Valida a consolidação v3 sem acessar Docker e sem usar dados reais de produção."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('indexar_v3', ROOT / 'scripts/indexar_v3.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def entry(year, idx):
    return {
        'id': hashlib.sha256(f'{year}/{idx}'.encode()).hexdigest(),
        'ano': year,
        'area': 'Computacao',
        'curso': 'Curso de teste',
        'tipo_formacao': 'CE',
        'numero_questao': idx % 40 + 1,
        'tipo_questao': 'objetiva',
        'enunciado': 'Questao de teste',
        'alternativas': [{'letra': 'A', 'texto': 'Exemplo'}],
        'pendente_revisao': True,
        'alertas': [],
        'origem': {'pdf_url': 'https://example.org/arquivo.pdf', 'pdf_sha256': 'a' * 64,
                   'pagina_inicial': 1, 'pagina_final': 1},
    }


def build(tmp_path):
    a = tmp_path / module.INPUTS[0][1]
    b = tmp_path / module.INPUTS[1][1]
    a.parent.mkdir(parents=True, exist_ok=True)
    b.parent.mkdir(parents=True, exist_ok=True)
    l1 = [entry(2023, i) for i in range(80)]
    l2 = [entry(2017, i) for i in range(80)] + [entry(2021, i) for i in range(120)]
    for f, data in ((a, l1), (b, l2)):
        f.write_text(''.join(json.dumps(q, ensure_ascii=False)+'\n' for q in data), encoding='utf-8')
    return a, b


def test_consolidacao_preserva_fonte_sem_aprovacao(tmp_path):
    a,b = build(tmp_path)
    before = (a.read_bytes(), b.read_bytes())
    items, report = module.prepare(tmp_path, persist=False)
    assert len(items) == 280
    assert len({q['id'] for q in items}) == 280
    assert report['por_ano'] == {'2017': 80, '2021': 120, '2023': 80}
    assert all(q['status_validacao'] == 'nao_revisada' for q in items)
    assert all(q['pendente_revisao'] is True and q['revisado_humanamente'] is False for q in items)
    assert (a.read_bytes(), b.read_bytes()) == before


def test_rejeita_duplicacao_entre_lotes(tmp_path):
    a,b = build(tmp_path)
    data = [json.loads(x) for x in b.read_text(encoding='utf-8').splitlines()]
    data[0]['id'] = json.loads(a.read_text(encoding='utf-8').splitlines()[0])['id']
    b.write_text(''.join(json.dumps(q, ensure_ascii=False)+'\n' for q in data), encoding='utf-8')
    import pytest
    with pytest.raises(ValueError, match='duplicado'):
        module.prepare(tmp_path, persist=False)


def test_rejeita_lote_incompleto(tmp_path):
    _, b = build(tmp_path)
    b.write_text('\n'.join(b.read_text(encoding='utf-8').splitlines()[:-1])+'\n', encoding='utf-8')
    import pytest
    with pytest.raises(ValueError, match='esperado 200'):
        module.prepare(tmp_path, persist=False)


def test_digest_independe_da_ordem_das_chaves():
    assert module.digest_json({'x': 1, 'y': 2}) == module.digest_json({'y': 2, 'x': 1})
