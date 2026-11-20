#!/usr/bin/env python3
"""Produz transcrições tabulares DESCRITIVAS e imagens vinculadas para 8 alvos RF04.

Não altera as 80 questões-fonte, o CSV humano ou índices Kafka/ES.
Toda transcrição permanece RASCUNHO até reconferência visual humana.
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
import hashlib
import html
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TRANSCRICOES = ROOT / "docs/RF04_TRANSCRICOES_ESTRUTURADAS.json"
CHAVES = {
    ("Agronomia", 3), ("Agronomia", 5), ("Agronomia", 26),
    ("Agronomia", 31), ("Agronomia", 32),
    ("Arquitetura e Urbanismo", 11), ("Arquitetura e Urbanismo", 17),
    ("Arquitetura e Urbanismo", 29),
}
IDS_PREFIXO = {
    ("Agronomia", 3): "f4908cfa17d5", ("Agronomia", 5): "c6623b2bad1a",
    ("Agronomia", 26): "e282d86f2865", ("Agronomia", 31): "f249a4d6587d",
    ("Agronomia", 32): "349e7e6bd861", ("Arquitetura e Urbanismo", 11): "3e8051b7524c",
    ("Arquitetura e Urbanismo", 17): "59a161e1e035", ("Arquitetura e Urbanismo", 29): "470111790def",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def ler_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def chave(q: dict) -> tuple[str, int]:
    return q.get("curso"), int(q.get("numero_questao", 0))


def transcricoes_validas(source: dict) -> dict[tuple[str, int], dict]:
    if source.get("versao") != 1:
        raise ValueError("Versão inesperada das transcrições")
    items = source.get("questoes")
    if not isinstance(items, list):
        raise ValueError("Transcrições inválidas")
    transcricoes = {}
    for v in items:
        k = chave(v)
        if k in transcricoes:
            raise ValueError(f"Questão duplicada na transcrição: {k}")
        colunas, linhas = v.get("colunas"), v.get("linhas")
        if not isinstance(colunas, list) or len(colunas) < 2 or not isinstance(linhas, list) or not linhas:
            raise ValueError(f"Tabela ausente ou inválida: {k}")
        if len(set(colunas)) != len(colunas) or any(not isinstance(c, str) or not c.strip() for c in colunas):
            raise ValueError(f"Colunas inválidas: {k}")
        if any(not isinstance(row, list) or len(row) != len(colunas) or any(not isinstance(cell, str) or not cell.strip() for cell in row) for row in linhas):
            raise ValueError(f"Dimensão da tabela inválida: {k}")
        if int(v.get("pagina_pdf", 0)) < 1 or not v.get("observacao") or not v.get("titulo"):
            raise ValueError(f"Metadados ausentes: {k}")
        transcricoes[k] = v
    if set(transcricoes) != CHAVES:
        raise ValueError(f"O catálogo deve cobrir os oito alvos RF04; encontrados {set(transcricoes)}")
    return transcricoes


def validar_percentuais(transcricoes: dict) -> None:
    q3 = transcricoes[("Agronomia", 3)]
    if q3["colunas"] != ["Imunizante", "Meta", "2017", "2018", "2019", "2020", "2021"] or len(q3["linhas"]) != 7:
        raise ValueError("Tabela de cobertura vacinal não possui 7 imunizantes e 5 anos")
    for row in q3["linhas"]:
        for percent in row[1:]:
            if not percent.endswith("%") or not 0 <= float(percent[:-1].replace(",", ".")) <= 100:
                raise ValueError("Percentual de vacinação inválido")
    q26 = transcricoes[("Agronomia", 26)]
    if len(q26["colunas"]) != 7 or len(q26["linhas"]) != 7:
        raise ValueError("Tabela agronômica exige 7 linhas e 6 colunas quantitativas")
    q32 = transcricoes[("Agronomia", 32)]
    total = sum(float(row[1].removesuffix("%").replace(",", ".")) for row in q32["linhas"])
    if abs(total - 100.0) > 0.001:
        raise ValueError(f"Os setores de captação devem somar 100%: {total}")
    q11 = transcricoes[("Arquitetura e Urbanismo", 11)]
    if [r[0] for r in q11["linhas"]] != list("ABCDE"):
        raise ValueError("As alternativas gráficas A–E devem estar identificadas")


def midias_verificadas(base: Path, q: dict) -> list[dict]:
    info = q.get("apresentacao_visual_rf04")
    if not isinstance(info, dict) or not info.get("referencias"):
        raise ValueError(f"Questão sem referência de mídia RF04: {q['id']}")
    if info.get("auditoria_original") != "enunciado_reprovado":
        raise ValueError("Avaliação original não identificada como reprovada")
    vistos: set[str] = set()
    assets: list[dict] = []
    for ref in info["referencias"]:
        raw = ref.get("arquivo", "")
        if not isinstance(raw, str) or not raw:
            raise ValueError("Caminho de imagem vazio")
        relativo = raw.replace("\\", "/")
        arquivo = (base / relativo).resolve()
        if not arquivo.is_relative_to(base.resolve()) or arquivo.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            raise ValueError(f"Caminho inseguro: {raw}")
        if not arquivo.is_file():
            raise FileNotFoundError(f"Imagem ausente: {raw}")
        atual = sha256(arquivo)
        if not ref.get("sha256") or ref["sha256"].lower() != atual:
            raise ValueError(f"SHA-256 de mídia não confere: {raw}")
        if relativo in vistos:
            raise ValueError(f"Imagem duplicada na apresentação: {raw}")
        vistos.add(relativo)
        assets.append(deepcopy(ref))
    return assets


def montar(dados: list[dict], auditoria: list[dict], transcricoes: dict, base: Path) -> tuple[list[dict], list[dict]]:
    if len(dados) != 80 or len({q["id"] for q in dados}) != 80:
        raise ValueError("Fonte RF04 precisa conter exatamente 80 IDs únicos")
    if len(auditoria) != 50 or len({q["id"] for q in auditoria}) != 50:
        raise ValueError("Auditoria precisa conter exatamente 50 IDs únicos")
    notas = {x["id"]: x for x in auditoria}
    saida = deepcopy(dados)
    eventos = []
    tratados = set()
    for i, q in enumerate(saida):
        k = chave(q)
        if k not in CHAVES:
            continue
        if k in tratados:
            raise ValueError(f"Questão repetida: {k}")
        tratados.add(k)
        if str(q.get("ano")) != "2023" or not q["id"].startswith(IDS_PREFIXO[k]):
            raise ValueError(f"Prova ou ID inesperado para {k}")
        nota = notas.get(q["id"])
        if not nota or nota.get("enunciado_correto_1_ou_0") != "0":
            raise ValueError(f"Ausência de avaliação humana 0 para enunciado: {k}")
        refs = midias_verificadas(base, q)
        t = transcricoes[k]
        if k == ("Arquitetura e Urbanismo", 11):
            letras = {r.get("letra") for r in refs if r.get("letra")}
            if letras != set("ABCDE"):
                raise ValueError("Faltam imagens das 5 alternativas A–E")
        if k == ("Arquitetura e Urbanismo", 17) and len(refs) < 2:
            raise ValueError("Questão 17 exige imagens dos dois segmentos de página")
        q["semantica_rf04"] = {
            "titulo": t["titulo"], "tipo": t["tipo_representacao"],
            "colunas": deepcopy(t["colunas"]), "linhas": deepcopy(t["linhas"]),
            "observacao": t["observacao"], "pagina_pdf": t["pagina_pdf"],
            "imagens": refs, "estado": "RASCUNHO_TECNICO_EXIGE_NOVA_REVISAO_HUMANA",
            "fonte": "Prova oficial ENADE 2023, com apoio da imagem associada e revisão da transcrição",
            "auditoria_original": "REPROVADA_MANTIDA",
        }
        q["pendente_revisao"] = True
        for alert in ("rf04_transcricao_estruturada_a_conferir",):
            if alert not in q.get("alertas", []):
                q.setdefault("alertas", []).append(alert)
        eventos.append({"id": q["id"], "curso": k[0], "numero_questao": k[1],
                        "pagina_pdf": t["pagina_pdf"], "linhas": len(t["linhas"]),
                        "imagens": len(refs), "status": "A_CONFERIR"})
    if tratados != CHAVES or len(eventos) != 8:
        raise ValueError(f"Questões esperadas {CHAVES}, encontradas {tratados}")
    original = {q["id"]: q for q in dados}
    for q in saida:
        o = original[q["id"]]
        if chave(q) not in CHAVES and q != o:
            raise AssertionError("Registro fora do escopo modificado")
        if chave(q) in CHAVES:
            x = deepcopy(q)
            x.pop("semantica_rf04", None)
            x["pendente_revisao"] = o["pendente_revisao"]
            x["alertas"] = o["alertas"]
            if x != o or q["id"] != o["id"] or q.get("enunciado") != o.get("enunciado") or q.get("alternativas") != o.get("alternativas"):
                raise AssertionError("Conteúdo original alterado indevidamente")
    return saida, eventos


def montar_html(registros: list[dict], base: Path, pagina: Path) -> str:
    cards: list[str] = []
    for q in registros:
        sem = q.get("semantica_rf04")
        if not sem:
            continue
        cabecalho = "".join("<th scope='col'>" + html.escape(cell) + "</th>" for cell in sem["colunas"])
        body = "".join("<tr>" + "".join("<td>" + html.escape(cell) + "</td>" for cell in row) + "</tr>" for row in sem["linhas"])
        figures = ""
        for r in sem["imagens"]:
            src = os.path.relpath((base / r["arquivo"]).resolve(), pagina.parent.resolve()).replace("\\", "/")
            desc = r.get("descricao") or r["arquivo"]
            letra = ("Alternativa " + str(r["letra"]) + " — ") if r.get("letra") else ""
            figures += ("<figure><img loading='lazy' src='" + html.escape(src, quote=True) + "' alt='" + html.escape(letra + str(desc), quote=True) + "'><figcaption>" + html.escape(letra + str(desc)) + "</figcaption></figure>")
        cards.append("<article><h2>" + html.escape(q["curso"]) + " — Questão " + str(q["numero_questao"]) + ": " + html.escape(sem["titulo"]) + "</h2><p class='tag'>RASCUNHO A CONFERIR • Original preservado</p>" +
                     "<h3>Dados e relações recuperados</h3><div class='scroll'><table><thead><tr>" + cabecalho + "</tr></thead><tbody>" + body + "</tbody></table></div>" +
                     "<p>" + html.escape(sem["observacao"]) + "</p><details open><summary>Imagens originais — referência obrigatória</summary><div class='images'>" + figures + "</div></details>" +
                     "<details><summary>Texto bruto original (não modificado)</summary><pre>" + html.escape(q.get("enunciado") or "") + "</pre></details></article>")
    return """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ENADE • RF04 • Transcrições estruturadas</title>
<style>body{font:15px/1.5 system-ui,Arial,sans-serif;background:#edf3f6;color:#102b42;margin:0}header{background:#103450;color:white;padding:24px}main{max-width:1150px;margin:24px auto;padding:0 15px}article{background:#fff;border:1px solid #d9e3eb;border-radius:12px;padding:22px;margin-bottom:20px}h2{margin-top:0}h3{margin-bottom:8px}.tag{color:#8b5d0a;font-weight:bold}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #cad6dc;padding:8px 10px;text-align:left;vertical-align:top}th{background:#e8f4f7}tr:nth-child(even) td{background:#f7fbfc}.images{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:12px;margin-top:12px}figure{margin:0;border:1px solid #d0dbe2;border-radius:8px;padding:8px}img{width:100%;height:auto}figcaption{font-size:12px;color:#516675}details{margin-top:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.45 ui-monospace,monospace;background:#f1f5f7;padding:12px}</style></head><body><header><h1>ENADE 2023 • Oito representações RF04</h1><p>Transcrições técnicas para conferência humana; nenhuma aprovação automática, índices intactos.</p></header><main>""" + "\n".join(cards) + "</main></body></html>"


def executar(base: Path, fonte: Path = TRANSCRICOES) -> dict:
    base = base.resolve()
    entrada = base / "data/extraidos_auditados_2023/questoes_visuais.jsonl"
    csvpath = base / "evidencias/A3_revisao_manual.csv"
    if not csvpath.is_file():
        raise FileNotFoundError(csvpath)
    dados = ler_jsonl(entrada)
    with csvpath.open(encoding="utf-8-sig", newline="") as stream:
        notas = list(csv.DictReader(stream))
    transcricoes = transcricoes_validas(json.loads(fonte.read_text(encoding="utf-8")))
    validar_percentuais(transcricoes)
    saida, itens = montar(dados, notas, transcricoes, base)
    destino = base / "data/extraidos_auditados_2023/questoes_semantica_rf04.jsonl"
    destino.parent.mkdir(parents=True, exist_ok=True)
    temp = destino.with_suffix(".jsonl.tmp")
    temp.write_text("".join(json.dumps(q, ensure_ascii=False, sort_keys=True) + "\n" for q in saida), encoding="utf-8")
    os.replace(temp, destino)
    galeria = base / "data/visuais_rf04/semantica.html"
    galeria.parent.mkdir(parents=True, exist_ok=True)
    galeria.write_text(montar_html(saida, base, galeria), encoding="utf-8")
    report = {
        "resultado": "8_TRANSCRICOES_ESTRUTURADAS_EM_RASCUNHO",
        "representacoes": len(itens), "registros": len(saida), "ids_preservados": True,
        "pendentes_validacao_humana": len(itens),
        "imagens_referenciadas": sum(x["imagens"] for x in itens),
        "fonte_sha256": sha256(entrada), "transcricoes_sha256": sha256(fonte),
        "auditoria_sha256": sha256(csvpath), "derivado_sha256": sha256(destino),
        "es_kafka_modificados": False, "auditoria_original_modificada": False,
        "aviso": "A revisão humana de 50 questões é uma evidência histórica e NÃO é aprovada retroativamente. Verificar manualmente cada tabela/descrição no PDF antes de aceite editorial.",
        "derivado": str(destino.relative_to(base)), "galeria": str(galeria.relative_to(base)),
        "questoes": itens,
    }
    saidarel = base / "evidencias/A3_rf04_semantica_rascunho.json"
    saidarel.parent.mkdir(parents=True, exist_ok=True)
    saidarel.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="Pasta original com data/ e evidencias/")
    args = parser.parse_args()
    try:
        report = executar(args.base)
        print(json.dumps({k:v for k,v in report.items() if k != "questoes"}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERRO: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
