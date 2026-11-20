#!/usr/bin/env python3
"""Coletor auditável de PDFs do ENADE: páginas oficiais do INEP -> manifesto -> downloads.

A etapa A2 NÃO extrai questões (A3) e NÃO realiza indexação Kafka/Elastic (A4).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

# Utiliza os certificados raiz confiáveis do Windows (ou do sistema hospedeiro)
# para validar HTTPS. Não desabilitar verificacao TLS em hipótese alguma.
# A injeção deve ocorrer ANTES da importação de requests/urllib3.
import truststore
truststore.inject_into_ssl()

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enade/provas-e-gabaritos"
MAX_PDF_BYTES = 45 * 1024 * 1024  # protecao contra arquivos inesperadamente enormes
FIELDS = ["ano", "curso", "tipo", "descricao", "url", "pagina_origem", "arquivo", "sha256", "bytes", "status", "erro", "obtido_em_utc"]
LOG = logging.getLogger("enade-coleta")


def ascii_slug(value: str) -> str:
    s = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "sem-identificacao"


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, connect=3, read=3, backoff_factor=1.0,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=frozenset(["GET"]))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "ENADE-BigDataII-academic-project/1.0 (public INEP PDFs)",
                      "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8"})
    return s


def is_official_pdf_url(raw_url: str) -> bool:
    p = urlparse(raw_url)
    host = (p.hostname or "").lower()
    # Evita downloads de terceiros ou esquemas não HTTP(S)
    return p.scheme in {"https", "http"} and (host == "gov.br" or host.endswith(".gov.br")) and ".pdf" in p.path.lower()


def infer_tipo(label: str, url: str) -> str | None:
    text = ascii_slug(label + " " + urlparse(url).path.split("/")[-1])
    if "gabarito" in text:
        return "gabarito"
    if "padrao" in text or "resposta" in text:
        return "padrao_resposta"
    if "diretriz" in text or "portaria" in text:
        return "diretriz"
    if "prova" in text or "caderno" in text:
        return "prova"
    return None


def maybe_course(text: str) -> str | None:
    t = re.sub(r"\s+", " ", text).strip(" :\t\r\n")
    lowered = ascii_slug(t)
    if not 3 <= len(t) <= 85 or len(t.split()) > 9:
        return None
    banned = ["prova", "gabarito", "padrao-de-resposta", "acessibilidade", "ampliada", "ledor", "inep", "enade", "compartilhe", "publicado-em", "atualizado-em", "questoes", "conteudo", "voltar", "menu", "republica", "inicio", "pesquisa", "governo-federal", "download"]
    if any(x in lowered for x in banned):
        return None
    if lowered.isdigit():
        return None
    return t


def parse_year_page(html: str, page_url: str, year: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    # Plone/gov.br: preferir região editorial, evitando menu e links de navegação
    scope = (soup.select_one("#parent-fieldname-text") or soup.select_one("#content-core")
             or soup.select_one("article") or soup.select_one("main") or soup)
    items = []
    seen = set()
    curso = None
    for node in scope.descendants:
        if not isinstance(node, Tag):
            continue
        # O INEP apresenta alguns cursos de 2021 como parágrafos simples, não
        # como <strong>/<h3>. Considerar parágrafos SEM links evita rotular
        # blocos que englobam provas e gabaritos como se fossem cursos.
        eh_titulo = node.name in {"strong", "h3", "h4", "h5"}
        eh_paragrafo_curso = (year == 2021 and node.name == "p" and
                              not node.find("a") and
                              ("(licenciatura)" in node.get_text(" ", strip=True).lower()
                               or "(bacharelado)" in node.get_text(" ", strip=True).lower()
                               or node.get_text(" ", strip=True).lower().startswith("tecnologia em ")))
        if (eh_titulo or eh_paragrafo_curso) and not node.find_parent("a"):
            candidate = maybe_course(node.get_text(" ", strip=True))
            if candidate:
                curso = candidate
        if node.name != "a" or not node.get("href"):
            continue
        url = urljoin(page_url, node.get("href", ""))
        if not is_official_pdf_url(url):
            continue
        label = node.get_text(" ", strip=True)
        tipo = infer_tipo(label, url)
        if not tipo or url in seen:
            continue
        seen.add(url)
        # Se a página mudou de layout e não há curso confiável, registrar 'nao_identificado'; não inventar.
        items.append({"ano": year, "curso": curso or "nao_identificado", "tipo": tipo,
                      "descricao": label, "url": url, "pagina_origem": page_url,
                      "arquivo": "", "sha256": "", "bytes": 0, "status": "catalogado",
                      "erro": "", "obtido_em_utc": ""})
    return items


def fetch_year(s: requests.Session, year: int) -> list[dict]:
    url = f"{BASE}/{year}"
    r = s.get(url, timeout=(15, 45))
    r.raise_for_status()
    result = parse_year_page(r.text, url, year)
    if not result:
        LOG.warning("Ano %s: nenhum link de PDF reconhecido; verifique o formato da pagina oficial %s", year, url)
    return result


def file_path(entry: dict, root: Path) -> Path:
    source = urlparse(entry["url"]).path
    suffix = hashlib.sha256(entry["url"].encode("utf-8")).hexdigest()[:12]
    simple = ascii_slug(Path(source).stem)[:45]
    name = f"{entry['ano']}_{ascii_slug(entry['curso'])}_{entry['tipo']}_{simple}_{suffix}.pdf"
    return root / str(entry["ano"]) / name


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_pdf(s: requests.Session, entry: dict, root: Path) -> dict:
    out = entry.copy()
    path = file_path(entry, root)
    out["arquivo"] = str(path.as_posix())
    temp = path.with_suffix(".pdf.part")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.is_file() and path.stat().st_size >= 5:
            with path.open("rb") as f:
                if f.read(5) == b"%PDF-":
                    out.update(status="existente", sha256=sha256_file(path), bytes=path.stat().st_size,
                               obtido_em_utc=datetime.now(timezone.utc).isoformat())
                    return out
        with s.get(entry["url"], stream=True, timeout=(15, 90), allow_redirects=True) as response:
            response.raise_for_status()
            if not is_official_pdf_url(response.url):
                raise ValueError("redirecionamento para URL nao oficial ou nao PDF")
            received = 0
            with temp.open("wb") as f:
                for chunk in response.iter_content(chunk_size=128 * 1024):
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > MAX_PDF_BYTES:
                        raise ValueError(f"PDF excede limite de {MAX_PDF_BYTES // (1024 * 1024)}MB")
                    f.write(chunk)
        with temp.open("rb") as f:
            if f.read(5) != b"%PDF-":
                raise ValueError("arquivo retornado nao possui assinatura PDF")
        os.replace(temp, path)
        out.update(status="baixado", sha256=sha256_file(path), bytes=path.stat().st_size,
                   obtido_em_utc=datetime.now(timezone.utc).isoformat())
    except (requests.RequestException, OSError, ValueError) as exc:
        out.update(status="falha", erro=f"{type(exc).__name__}: {exc}")
        LOG.error("Falha em %s: %s", entry["url"], exc)
        temp.unlink(missing_ok=True)
    return out


def carregar_manifesto(outdir: Path) -> list[dict]:
    """Recupera o estado anterior, impedindo perda de hashes ao catalogar outros anos."""
    p = outdir / "catalogo_enade.csv"
    if not p.is_file():
        return []
    with p.open("r", encoding="utf-8-sig", newline="") as stream:
        return [r for r in csv.DictReader(stream) if r.get("url")]


def mesclar_manifesto(anteriores: list[dict], novos: list[dict], root_pdf: Path) -> list[dict]:
    """Mantem URLs historicas e reaproveita status somente se o PDF/hash ainda existem."""
    by_url: dict[str, dict] = {}
    for old in anteriores:
        url = old.get("url")
        if url:
            by_url[url] = {k: old.get(k, "") for k in FIELDS}
    for novo in novos:
        url = novo["url"]
        anterior = by_url.get(url)
        if not anterior:
            by_url[url] = novo.copy()
            continue
        result = anterior.copy()
        # Dados da descoberta atual podem melhorar, mas nao devem apagar o curso identificado.
        for key in ("ano", "tipo", "descricao", "pagina_origem"):
            if novo.get(key):
                result[key] = novo[key]
        if novo.get("curso") and novo["curso"] != "nao_identificado":
            result["curso"] = novo["curso"]
        if novo.get("status") in ("baixado", "existente"):
            result.update({k: novo.get(k, "") for k in
                           ("arquivo", "sha256", "bytes", "status", "erro", "obtido_em_utc")})
        elif novo.get("status") == "falha":
            result["erro"] = novo.get("erro", "")
            if result.get("status") not in ("baixado", "existente"):
                result["status"] = "falha"
        by_url[url] = result
    for row in by_url.values():
        if row.get("status") in ("baixado", "existente"):
            # Nome determinado pela URL e pelo curso original; o manifesto armazena
            # o caminho real, nao usar 'file_path' para reconstruir um nome mutavel.
            caminho = Path(row.get("arquivo") or "")
            if not caminho.is_absolute():
                caminho = Path.cwd() / caminho
            valid = (caminho.is_file() and row.get("sha256") and
                     sha256_file(caminho) == row["sha256"])
            if not valid:
                row["status"] = "catalogado"
                row["erro"] = "arquivo_local_ausente_ou_hash_divergente"
                row["sha256"] = ""
                row["bytes"] = 0
    return list(by_url.values())


def write_manifest(items: list[dict], outdir: Path) -> None:
    """Substituicao atomica para nao corromper o catalogo existente."""
    outdir.mkdir(parents=True, exist_ok=True)
    csvfile = outdir / "catalogo_enade.csv"
    jsonlfile = outdir / "catalogo_enade.jsonl"
    csvtemp = csvfile.with_suffix(".csv.tmp")
    jsontemp = jsonlfile.with_suffix(".jsonl.tmp")
    with csvtemp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(items)
    with jsontemp.open("w", encoding="utf-8") as f:
        for entry in items:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    os.replace(csvtemp, csvfile)
    os.replace(jsontemp, jsonlfile)
    print(f"Manifestos acumulativos: {csvfile} e {jsonlfile}")


def filtrar_por_curso(items: list[dict], nomes_cursos: list[str]) -> list[dict]:
    """Seleciona apenas cursos contendo nomes normalizados informados pelo usuario."""
    filtros = [ascii_slug(nome.strip()) for nome in nomes_cursos if nome.strip()]
    if not filtros:
        return items
    return [item for item in items if any(
        filtro in ascii_slug(item.get("curso", "")) for filtro in filtros
    )]


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(description="Coleta rastreavel do acervo publico ENADE INEP")
    p.add_argument("--anos", default="2023", help="Anos separados por virgula, ex.: 2023,2022,2021")
    p.add_argument("--limite", type=int, default=3, help="Maximo de PDFs por execucao (0 = sem limite)")
    p.add_argument("--somente-catalogo", action="store_true", help="Apenas listar PDFs oficiais, sem baixar")
    p.add_argument("--somente-pendentes", action="store_true",
                   help="Priorizar PDFs ainda nao presentes com hash valido no manifesto")
    p.add_argument("--sem-acessibilidade", action="store_true",
                   help="Ignorar versoes alternativas (ledor, ampliada, braille etc.) nos downloads")
    p.add_argument("--tipos", default="",
                   help="Restringir downloads a tipos separados por virgula (prova,gabarito,padrao_resposta,diretriz)")
    p.add_argument("--cursos", default="",
                   help="Filtrar cursos por nomes ou partes de nomes, separados por virgula; ignora acentos e caixa")
    p.add_argument("--listar-selecao", action="store_true",
                   help="Exibir os proximos arquivos elegiveis sem baixar ou modificar manifestos")
    p.add_argument("--pausa", type=float, default=0.4, help="Intervalo entre downloads em segundos")
    p.add_argument("--saida", type=Path, default=Path("data/raw"), help="Pasta de PDFs")
    p.add_argument("--manifestos", type=Path, default=Path("data/manifests"), help="Pasta dos manifestos")
    args = p.parse_args(argv)
    if args.limite < 0 or args.pausa < 0:
        p.error("--limite e --pausa devem ser >= 0")
    args.tipos_permitidos = {t.strip().lower() for t in args.tipos.split(",") if t.strip()}
    args.cursos_filtro = [x.strip() for x in args.cursos.split(",") if x.strip()]
    permitidos = {"prova", "gabarito", "padrao_resposta", "diretriz"}
    if args.tipos_permitidos - permitidos:
        p.error("--tipos aceita apenas prova,gabarito,padrao_resposta,diretriz")
    try:
        args.years = list(dict.fromkeys(int(x.strip()) for x in args.anos.split(",") if x.strip()))
    except ValueError:
        p.error("--anos exige numeros separados por virgula")
    if not args.years or any(y < 2004 or y > 2026 for y in args.years):
        p.error("Ano fora do intervalo esperado (2004 a 2026)")
    return args


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    s = session()
    files: list[dict] = []
    errors = 0
    for year in args.years:
        try:
            matches = fetch_year(s, year)
            print(f"{year}: {len(matches)} links oficiais catalogados")
            files.extend(matches)
        except requests.RequestException as exc:
            errors += 1
            LOG.error("Falha ao consultar pagina %s: %s", year, exc)
    if not files:
        LOG.error("Nenhum PDF catalogado. Verifique conexao e pagina INEP.")
        return 1
    anteriores = carregar_manifesto(args.manifestos)
    # Valida hashes ja registrados, inclusive quando a verificacao e apenas de planejamento.
    estado = mesclar_manifesto(anteriores, files, args.saida)
    existentes_validos = {row["url"] for row in estado
                        if row.get("status") in ("baixado", "existente")}
    candidatos = filtrar_por_curso(files, args.cursos_filtro)
    if args.tipos_permitidos:
        candidatos = [row for row in candidatos if row["tipo"] in args.tipos_permitidos]
    if args.sem_acessibilidade:
        marcas = ("ledor", "braille", "ampliada", "ampliado",
                  "superampliada", "superampliado", "libras")
        candidatos = [row for row in candidatos if not any(
            m in (ascii_slug(row.get("descricao", "")) + " " +
                  ascii_slug(Path(urlparse(row.get("url", "")).path).name))
            for m in marcas)]
    if args.somente_pendentes:
        candidatos = [row for row in candidatos if row["url"] not in existentes_validos]
    targets = candidatos if args.limite == 0 else candidatos[:args.limite]
    print(f"Selecionados={len(targets)}; elegiveis={len(candidatos)}; "
          f"existentes_validos={len(existentes_validos)}; anos={','.join(map(str, args.years))}")
    if args.listar_selecao:
        for n, item in enumerate(targets, 1):
            print(f"[{n}/{len(targets)}] {item['ano']} | {item['curso']} | "
                  f"{item['tipo']} | {item['url']}")
        print("Somente planejamento: nenhum PDF baixado ou manifesto alterado.")
        return 0
    processed = {}
    if not args.somente_catalogo:
        for n, item in enumerate(targets, 1):
            print(f"[{n}/{len(targets)}] {item['ano']} {item['curso']} - {item['tipo']}")
            # Preservar o curso já identificado no manifesto para que o nome
            # do PDF não mude só porque uma nova consulta perdeu o cabeçalho.
            anterior = next((r for r in estado if r["url"] == item["url"]), None)
            item_para_download = item.copy()
            if anterior and anterior.get("curso") not in (None, "", "nao_identificado"):
                item_para_download["curso"] = anterior["curso"]
            result = download_pdf(s, item_para_download, args.saida)
            processed[item["url"]] = result
            if result["status"] == "falha":
                errors += 1
            if n < len(targets):
                time.sleep(args.pausa)
    output_novo = [processed.get(item["url"], item) for item in files]
    output = mesclar_manifesto(anteriores, output_novo, args.saida)
    write_manifest(output, args.manifestos)
    ok = sum(row["status"] in ("baixado", "existente") for row in output)
    missing_course = sum(row["curso"] == "nao_identificado" for row in output)
    print(f"Resumo acumulativo: catalogados={len(output)}, baixados_ou_existentes={ok}, falhas_na_execucao={errors}, cursos_nao_identificados={missing_course}")
    print("Obs.: catalogado nao significa baixado. Qualidade da extracao e validacao de metadados sao etapas seguintes.")
    return 1 if errors or (not args.somente_catalogo and not ok) else 0


if __name__ == "__main__":
    sys.exit(main())
