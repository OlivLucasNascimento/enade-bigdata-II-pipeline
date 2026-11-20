import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "coletar_enade.py"
spec = importlib.util.spec_from_file_location("coletar_enade", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HTML = '''<html><body><div id="parent-fieldname-text">
<p><strong>Enfermagem</strong></p><ul>
<li><a href="https://download.inep.gov.br/enade/provas/2023/enfermagem_prova.pdf">Prova</a></li>
<li><a href="https://download.inep.gov.br/enade/gabaritos/2023/enfermagem_gabarito.pdf">Gabarito</a></li>
<li><a href="https://download.inep.gov.br/enade/provas/2023/enfermagem_prova.pdf">Prova repetida</a></li>
</ul><p><strong>Biomedicina</strong></p><ul>
<li><a href="https://download.inep.gov.br/enade/provas/2023/biomedicina.pdf">Prova</a></li>
<li><a href="https://outro-site.org/enganoso.pdf">Prova externa</a></li>
</ul></div></body></html>'''


def test_discovery_and_dedup():
    entries = mod.parse_year_page(HTML, mod.BASE + "/2023", 2023)
    assert len(entries) == 3
    assert [x["curso"] for x in entries] == ["Enfermagem", "Enfermagem", "Biomedicina"]
    assert [x["tipo"] for x in entries] == ["prova", "gabarito", "prova"]


def test_allowed_domains():
    assert mod.is_official_pdf_url("https://download.inep.gov.br/abc.pdf")
    assert not mod.is_official_pdf_url("https://inep.gov.br.evil.com/abc.pdf")
    assert not mod.is_official_pdf_url("file:///local.pdf")
    assert not mod.is_official_pdf_url("https://download.inep.gov.br/index.html")


def test_deterministic_filename(tmp_path):
    entry = mod.parse_year_page(HTML, mod.BASE + "/2023", 2023)[0]
    a = mod.file_path(entry, tmp_path)
    b = mod.file_path(entry, tmp_path)
    assert a == b
    assert "2023" in a.name
    assert a.suffix == ".pdf"
    assert a.parent == tmp_path / "2023"


def test_download_mock(tmp_path):
    class Response:
        url = "https://download.inep.gov.br/teste.pdf"
        def raise_for_status(self): pass
        def iter_content(self, chunk_size): yield b"%PDF-1.7\nexemplo\n%%EOF\n"
        def __enter__(self): return self
        def __exit__(self, *args): return False
    class Session:
        def get(self, *args, **kwargs): return Response()
    e = {"ano": 2023, "curso": "Enfermagem", "tipo": "prova", "url": Response.url}
    first = mod.download_pdf(Session(), e, tmp_path)
    second = mod.download_pdf(Session(), e, tmp_path)
    assert first["status"] == "baixado"
    assert second["status"] == "existente"
    assert first["sha256"] == second["sha256"]
    assert first["bytes"] > 5


def test_tls_verification_remains_enabled():
    s = mod.session()
    assert s.verify is True, 'A verificacao TLS nao pode ser desabilitada'
