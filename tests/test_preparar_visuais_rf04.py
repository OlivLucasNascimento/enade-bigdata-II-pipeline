"""Testes que não exigem PDFs, Kafka ou arquivos privados."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import pytest

MOD = Path(__file__).resolve().parents[1] / "scripts" / "preparar_visuais_rf04.py"
sp = importlib.util.spec_from_file_location("preparar_visuais_rf04", MOD)
rf04 = importlib.util.module_from_spec(sp)
sp.loader.exec_module(rf04)


def img(tmp_path, name="data/midias/teste.png"):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"PNG-TESTE")
    return name, hashlib.sha256(p.read_bytes()).hexdigest()


def test_referencias_integras(tmp_path):
    name, h = img(tmp_path)
    q = {"midias": [{"arquivo": name, "imagem_sha256": h, "tipo": "pagina_pdf_renderizada"}]}
    refs = rf04.referencias(tmp_path, q)
    assert len(refs) == 1 and refs[0]["sha256"] == h


def test_detecta_hash_divergente(tmp_path):
    name, h = img(tmp_path)
    with pytest.raises(ValueError, match="divergente"):
        rf04.referencias(tmp_path, {"midias": [{"arquivo": name, "imagem_sha256": "0" * 64}]})


def test_detecta_imagem_ausente(tmp_path):
    with pytest.raises(FileNotFoundError, match="ausente"):
        rf04.referencias(tmp_path, {"midias": [{"arquivo": "data/midias/nada.png"}]})


def test_impede_escapar_da_raiz(tmp_path):
    with pytest.raises(ValueError, match="fora da pasta"):
        rf04.arquivo_seguro(tmp_path, "../segredo.png")


def test_evitar_imagens_duplicadas(tmp_path):
    name, h = img(tmp_path)
    q = {"midias": [{"arquivo": name, "imagem_sha256": h}, {"arquivo": name, "imagem_sha256": h}]}
    assert len(rf04.referencias(tmp_path, q)) == 1


def test_alternativa_grafica_referencia(tmp_path):
    name, h = img(tmp_path)
    q = {"midias": [], "alternativas": [{"letra": "A", "imagem": name}]}
    assert rf04.referencias(tmp_path, q)[0]["letra"] == "A"


def test_galeria_html_saneia_texto(tmp_path):
    name, h = img(tmp_path)
    q = {"curso": "Agronomia", "numero_questao": 3, "enunciado": "<script>alert(1)</script>",
         "apresentacao_visual_rf04": {"titulo": "Teste", "referencias": [
             {"arquivo": name, "descricao": "Teste", "letra": None}]},
         "alternativas": []}
    doc = rf04.galeria(tmp_path, [q], tmp_path / "data/visuais_rf04/galeria.html")
    assert "&lt;script&gt;" in doc and "<script>alert" not in doc
