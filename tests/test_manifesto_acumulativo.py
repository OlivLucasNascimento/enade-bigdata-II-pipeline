import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'coletar_enade.py'
spec = importlib.util.spec_from_file_location('coletar_enade', PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_catalogo_acumulativo_preserva_hash_ano_anterior(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    name = tmp_path / 'data/raw/2023/enade_prova.pdf'
    name.parent.mkdir(parents=True)
    name.write_bytes(b'%PDF-1.7\nconteudo')
    fonte = dict(ano=2023, curso='Agronomia', tipo='prova', descricao='Prova',
                 url='https://download.inep.gov.br/arquivo.pdf', pagina_origem='https://gov.br/2023',
                 arquivo=str(name.relative_to(tmp_path)), sha256=mod.sha256_file(name), bytes=name.stat().st_size,
                 status='baixado', erro='', obtido_em_utc='2026-11-18')
    novo = dict(ano=2021, curso='Biomedicina', tipo='prova', descricao='Prova',
                url='https://download.inep.gov.br/outro.pdf',pagina_origem='https://gov.br/2021',
                arquivo='',sha256='',bytes=0,status='catalogado',erro='',obtido_em_utc='')
    combinado = mod.mesclar_manifesto([fonte], [novo], tmp_path / 'data/raw')
    assert len(combinado) == 2
    assert combinado[0]['sha256'] == fonte['sha256']
    assert combinado[0]['status'] == 'baixado'
    mod.write_manifest(combinado, tmp_path / 'data/manifests')
    assert len(mod.carregar_manifesto(tmp_path / 'data/manifests')) == 2


def test_manifesto_invalido_nao_e_marcado_baixado(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fonte = dict(ano=2023, curso='Agronomia', tipo='prova', descricao='Prova',
                 url='https://download.inep.gov.br/arquivo.pdf', pagina_origem='',
                 arquivo='data/raw/2023/ausente.pdf', sha256='a'*64, bytes=100,
                 status='baixado', erro='', obtido_em_utc='')
    assert mod.mesclar_manifesto([fonte], [], tmp_path / 'data/raw')[0]['status'] == 'catalogado'
