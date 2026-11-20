#!/usr/bin/env python3
"""Valida referências visuais e prepara visualização offline das 8 pendências A3.

Não modifica fontes, PDFs, auditoria ou Elasticsearch. NÃO converte semanticamente
imagens em tabelas ou diagramas e NÃO reclassifica a aprovação humana.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
from copy import deepcopy
from pathlib import Path

ALVOS = {
    ("Agronomia", 3): ("Gráfico de vacinação infantil", "grafico_barras"),
    ("Agronomia", 5): ("Infográfico de mobilidade urbana", "infografico"),
    ("Agronomia", 26): ("Tabela de nutrientes por tratamento e ano", "tabela"),
    ("Agronomia", 31): ("Curva das fases de germinação", "grafico_curva"),
    ("Agronomia", 32): ("Distribuição de captação de água", "grafico_setorial"),
    ("Arquitetura e Urbanismo", 11): ("Planta de cobertura e cinco alternativas gráficas", "plantas_alternativas"),
    ("Arquitetura e Urbanismo", 17): ("Plantas e fachadas arquitetônicas", "desenho_tecnico"),
    ("Arquitetura e Urbanismo", 29): ("Diagrama de transmissão acústica", "diagrama"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def arquivo_seguro(base: Path, relativo: str) -> Path:
    if not isinstance(relativo, str) or not relativo.strip():
        raise ValueError("Caminho de mídia vazio")
    destino = (base / relativo).resolve()
    if not destino.is_relative_to(base.resolve()):
        raise ValueError(f"Mídia fora da pasta de dados: {relativo}")
    if not destino.is_file():
        raise FileNotFoundError(f"Mídia ausente: {relativo}")
    if destino.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        raise ValueError(f"Formato de mídia inesperado: {relativo}")
    return destino


def referencias(base: Path, q: dict) -> list[dict]:
    """Preserva a primeira descrição por arquivo e valida todos os SHA declarados."""
    vistos: dict[str, dict] = {}
    for m in q.get("midias") or []:
        if not isinstance(m, dict) or not m.get("arquivo"):
            continue
        relativo = m["arquivo"].replace("\\", "/")
        caminho = arquivo_seguro(base, relativo)
        atual = sha256(caminho)
        esperado = m.get("imagem_sha256")
        if esperado and atual.lower() != str(esperado).lower():
            raise ValueError(f"SHA-256 divergente: {relativo}")
        if relativo not in vistos:
            vistos[relativo] = {
                "arquivo": relativo,
                "sha256": atual,
                "tipo": m.get("tipo") or "imagem_referenciada",
                "pagina": m.get("pagina"),
                "letra": m.get("letra"),
                "descricao": m.get("descricao") or "Referência ao PDF original",
            }
    for alt in q.get("alternativas") or []:
        relativo = (alt.get("imagem") or "").replace("\\", "/")
        if not relativo:
            continue
        caminho = arquivo_seguro(base, relativo)
        atual = sha256(caminho)
        if relativo not in vistos:
            vistos[relativo] = {
                "arquivo": relativo, "sha256": atual,
                "tipo": "alternativa_grafica_png", "pagina": None,
                "letra": alt.get("letra"), "descricao": "Alternativa gráfica do PDF original",
            }
    return list(vistos.values())


def avaliar_registros(dados: list[dict], auditoria: list[dict], base: Path) -> tuple[list[dict], list[dict]]:
    if len(dados) != 80 or len({x.get("id") for x in dados}) != 80:
        raise ValueError("Esperados exatamente 80 registros únicos de 2023")
    if len(auditoria) != 50 or len({x.get("id") for x in auditoria}) != 50:
        raise ValueError("A amostra deve possuir 50 IDs distintos")
    amostra = {x["id"]: x for x in auditoria}
    saida = deepcopy(dados)
    relatorio = []
    identificados = set()
    for q in saida:
        chave = (q.get("curso"), int(q.get("numero_questao") or 0))
        if str(q.get("ano")) != "2023" or chave not in ALVOS:
            continue
        if chave in identificados:
            raise ValueError(f"Questão alvo repetida: {chave}")
        identificados.add(chave)
        nota = amostra.get(q["id"])
        if not nota or nota.get("enunciado_correto_1_ou_0") != "0":
            raise ValueError(f"Alvo sem reprovação do enunciado na auditoria: {chave}")
        assets = referencias(base, q)
        if not assets:
            raise ValueError(f"Questão sem imagem vinculada: {chave}")
        if chave == ("Arquitetura e Urbanismo", 11):
            alt = q.get("alternativas") or []
            if len(alt) != 5 or {a.get("letra") for a in alt} != set("ABCDE") or any(not a.get("imagem") for a in alt):
                raise ValueError("Questão 11 deve ter cinco alternativas gráficas A-E associadas")
        titulo, tipo = ALVOS[chave]
        q["apresentacao_visual_rf04"] = {
            "titulo": titulo,
            "categoria": tipo,
            "referencias": assets,
            "estado": "IMAGENS_VALIDAS_SEM_CONVERSAO_SEMANTICA_COMPLETA",
            "semantica_pendente": True,
            "auditoria_original": "enunciado_reprovado",
            "nota": "A imagem continua necessária para interpretação; referências não equivalem a LaTeX/Mermaid/Markdown validado.",
        }
        q["pendente_revisao"] = True
        alertas = list(q.get("alertas") or [])
        if "rf04_semantica_visual_pendente" not in alertas:
            alertas.append("rf04_semantica_visual_pendente")
        q["alertas"] = alertas
        relatorio.append({
            "id": q["id"], "curso": chave[0], "numero_questao": chave[1],
            "categoria": tipo, "arquivos_unicos": len(assets),
            "alternativas_graficas": sum(bool(a.get("imagem")) for a in q.get("alternativas") or []),
            "imagens_verificadas": [a["arquivo"] for a in assets],
            "revisao_semantica": "PENDENTE",
        })
    if identificados != set(ALVOS) or len(relatorio) != 8:
        raise ValueError(f"Esperadas 8 questões de RF04; encontradas {len(relatorio)}: {identificados}")
    if [q["id"] for q in dados] != [q["id"] for q in saida]:
        raise AssertionError("IDs ou ordem alterados")
    por_id = {q["id"]: q for q in dados}
    for q in saida:
        if (q.get("curso"), int(q.get("numero_questao") or 0)) not in ALVOS and q != por_id[q["id"]]:
            raise AssertionError("Alteração fora das oito questões")
    return saida, relatorio


def galeria(base: Path, registros: list[dict], saida: Path) -> str:
    fragments = []
    for q in registros:
        info = q.get("apresentacao_visual_rf04")
        if not info:
            continue
        blocos = []
        for m in info["referencias"]:
            alvo = arquivo_seguro(base, m["arquivo"])
            rel = Path(os.path.relpath(alvo, saida.parent)).as_posix()
            nome = html.escape(str(m.get("descricao") or m["arquivo"]))
            letra = f"Alternativa {html.escape(str(m['letra']))}: " if m.get("letra") else ""
            blocos.append(f'<figure><img loading="lazy" src="{html.escape(rel, quote=True)}" alt="{letra}{nome}"><figcaption>{letra}{nome}</figcaption></figure>')
        alt_html = "".join(
            f'<li>{html.escape(str(a.get("letra", "")))}: {html.escape(str(a.get("texto", "")))}</li>'
            for a in q.get("alternativas") or []
        )
        fragments.append(f'''<article>
<h2>{html.escape(q["curso"])} — Questão {int(q["numero_questao"])}: {html.escape(info["titulo"])}</h2>
<p class="status">Arquivos verificados por SHA-256. Semântica visual pendente de revisão; nota da auditoria original preservada.</p>
<div class="imggrid">{"".join(blocos)}</div>
<details><summary>Enunciado extraído (texto)</summary><pre>{html.escape(q.get("enunciado") or "")}</pre></details>
<details><summary>Alternativas</summary><ol>{alt_html}</ol></details>
</article>''')
    return '''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8" />
<title>ENADE — Conferência de mídia RF04</title><style>
body{margin:0;font:15px/1.5 system-ui,Arial,sans-serif;color:#173045;background:#e9eff3}
header{background:#102f46;color:#fff;padding:18px 24px}main{max-width:1200px;margin:auto;padding:18px}
article{background:#fff;margin-bottom:24px;padding:22px;border-radius:12px;border:1px solid #d5e1e7}
h2{margin:0 0 10px}.status{color:#84510b}.imggrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}
figure{margin:0;border:1px solid #d9e1e9;padding:8px;border-radius:8px}
figure img{max-width:100%;width:100%;height:auto}figcaption{font-size:12px;color:#4b6578}
pre{white-space:pre-wrap;word-break:break-word;background:#f2f6f8;padding:14px}details{margin-top:12px}
</style></head><body><header><h1>ENADE — 8 elementos visuais do RF04</h1><p>Galeria local de conferência • imagens existentes • nenhum enunciado automaticamente aprovado</p></header><main>''' + "\n".join(fragments) + '</main></body></html>'


def executar(base: Path) -> dict:
    base = base.resolve()
    origem = base / "data/extraidos_auditados_2023/questoes.jsonl"
    csvpath = base / "evidencias/A3_revisao_manual.csv"
    if not origem.is_file() or not csvpath.is_file():
        raise FileNotFoundError("Faltam JSONL derivado (pós-correção de rascunhos) ou CSV da auditoria")
    registros = [json.loads(s) for s in origem.read_text(encoding="utf-8-sig").splitlines() if s.strip()]
    with csvpath.open(encoding="utf-8-sig", newline="") as stream:
        auditoria = list(csv.DictReader(stream))
    saida, itens = avaliar_registros(registros, auditoria, base)
    dest = base / "data/extraidos_auditados_2023/questoes_visuais.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in saida), encoding="utf-8")
    os.replace(tmp, dest)
    visual = base / "data/visuais_rf04/galeria.html"
    visual.parent.mkdir(parents=True, exist_ok=True)
    visual.write_text(galeria(base, saida, visual), encoding="utf-8")
    report = {
        "resultado": "INTEGRIDADE_VISUAL_APROVADA_SEMANTICA_PENDENTE",
        "questoes_visuais": 8,
        "imagens_unicas_referenciadas": sum(x["arquivos_unicos"] for x in itens),
        "arquivos_ausentes": 0, "hashes_divergentes": 0,
        "ids_preservados": True, "total_registros": len(saida),
        "sha256_csv_auditoria": sha256(csvpath),
        "sha256_origem_derivada": sha256(origem),
        "sha256_saida_visual": sha256(dest),
        "indice_elasticsearch_alterado": False,
        "aprovacao_editorial": "PENDENTE",
        "aviso": "Confere integridade e associação dos arquivos, não interpreta automaticamente os gráficos ou os diagramas.",
        "jsonl_derivado": str(dest.relative_to(base)),
        "galeria_html": str(visual.relative_to(base)),
        "questoes": itens,
    }
    rep = base / "evidencias/A3_rf04_visuais_integridade.json"
    rep.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="Pasta do projeto original (contém data/ e evidencias/)")
    args = parser.parse_args()
    result = executar(args.base)
    print(json.dumps({k: v for k, v in result.items() if k != "questoes"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
