"""Testes unitários do enriquecimento semântico RF04 (não substituem a revisão dos PDFs)."""
from __future__ import annotations
import csv
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/estruturar_semantica_rf04.py"
CATALOG = Path(__file__).resolve().parents[1] / "docs/RF04_TRANSCRICOES_ESTRUTURADAS.json"
spec = importlib.util.spec_from_file_location("estruturar_semantica_rf04", SCRIPT)
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)


def dados_catalogo():
    return rf.transcricoes_validas(json.loads(CATALOG.read_text(encoding="utf-8")))


def criar_dataset(tmp_path):
    catalogo = dados_catalogo()
    dataset = []
    notas = []
    for k in sorted(rf.CHAVES):
        id_ = rf.IDS_PREFIXO[k] + "0" * (64-len(rf.IDS_PREFIXO[k]))
        refs=[]
        for i in range(6 if k == ("Arquitetura e Urbanismo", 11) else 2 if k == ("Arquitetura e Urbanismo", 17) else 1):
            nome = f"midias/{id_[:12]}_{i}.png"
            p=tmp_path / nome;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((f"png-{i}-{id_}").encode())
            ref={"arquivo":nome,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"descricao":"Página"}
            if k == ("Arquitetura e Urbanismo",11) and i:
                ref["letra"]="ABCDE"[i-1]
            refs.append(ref)
        dataset.append({"id":id_,"curso":k[0],"ano":2023,"numero_questao":k[1],"enunciado":"original", "alternativas":[{"letra":x,"texto":"original"} for x in "ABCDE"],"midias":[],"alertas":["revisar"],"pendente_revisao":True,"apresentacao_visual_rf04":{"referencias":refs,"auditoria_original":"enunciado_reprovado"}})
        notas.append({"id":id_,"enunciado_correto_1_ou_0":"0"})
    for j in range(72):
        dataset.append({"id":f"ex{j:062d}","curso":"Outro","ano":2023,"numero_questao":j+1,"enunciado":"x","alternativas":[],"alertas":[],"pendente_revisao":False})
    for j in range(42):notas.append({"id":dataset[j+8]["id"],"enunciado_correto_1_ou_0":"1"})
    return dataset,notas,catalogo


def test_catalogo_oito_ids():
    assert set(dados_catalogo()) == rf.CHAVES


def test_integridade_percentuais():
    rf.validar_percentuais(dados_catalogo())


def test_vacinacao_2017_2021():
    rows=dados_catalogo()[("Agronomia",3)]["linhas"]
    assert rows[0][2]=="97,98%" and rows[0][-1]=="65,93%"
    assert rows[3][-1]=="5,70%"


def test_tab_nutrientes():
    t=dados_catalogo()[("Agronomia",26)]
    assert t["linhas"][3][1:]==["9,37 a", "12,73 a", "1,55 a", "1,25 bc", "9,63 a", "7,90 b"]


def test_setores_somam_100():
    rf.validar_percentuais(dados_catalogo())
    assert len(dados_catalogo()[("Agronomia",32)]["linhas"])==7


def test_montar_preserva_80(tmp_path):
    orig, notas, cat=criar_dataset(tmp_path)
    deriv, events=rf.montar(orig,notas,cat,tmp_path)
    assert len(events)==8 and len(deriv)==80
    assert orig != deriv and orig[0].get("semantica_rf04") is None
    assert deriv[0]["semantica_rf04"]["estado"].startswith("RASCUNHO")
    assert orig[9]==deriv[9]
    assert orig[0]["enunciado"]==deriv[0]["enunciado"]


def test_montar_reprova_hash_trocado(tmp_path):
    orig,notas,cat=criar_dataset(tmp_path)
    p=tmp_path/orig[0]["apresentacao_visual_rf04"]["referencias"][0]["arquivo"]
    p.write_bytes(b"alterado")
    try:rf.montar(orig,notas,cat,tmp_path)
    except ValueError as exc:assert "SHA-256" in str(exc)
    else:assert False,"hash divergente deve falhar"


def test_nao_reclassifica_auditoria(tmp_path):
    orig,notas,cat=criar_dataset(tmp_path)
    deriv,_=rf.montar(orig,notas,cat,tmp_path)
    assert all(q["pendente_revisao"] for q in deriv if rf.chave(q) in rf.CHAVES)
    assert all(q["semantica_rf04"]["auditoria_original"]=="REPROVADA_MANTIDA" for q in deriv if "semantica_rf04" in q)


def test_imagens_alt_html(tmp_path):
    orig, notas, cat = criar_dataset(tmp_path)
    deriv,_=rf.montar(orig,notas,cat,tmp_path)
    page=tmp_path/"data/visuais_rf04/semantica.html"
    s=rf.montar_html(deriv,tmp_path,page)
    assert "Alternativa E" in s and "97,98%" in s and "49,8%" in s
    assert "RASCUNHO A CONFERIR" in s


def test_sem_diagrama_nao_corrigir_so_texto():
    t=dados_catalogo()[("Arquitetura e Urbanismo",11)]
    assert "não substituíveis" in t["observacao"]


def test_fluxo_completo_cria_artefatos_sem_mudar_fonte(tmp_path):
    dados,notas,cat=criar_dataset(tmp_path)
    fonte = tmp_path / "data/extraidos_auditados_2023/questoes_visuais.jsonl"
    fonte.parent.mkdir(parents=True,exist_ok=True)
    csvfile=tmp_path/"evidencias/A3_revisao_manual.csv"
    csvfile.parent.mkdir(parents=True,exist_ok=True)
    fonte.write_text("".join(json.dumps(q,ensure_ascii=False)+"\n" for q in dados),encoding="utf-8")
    with csvfile.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["id","enunciado_correto_1_ou_0"])
        w.writeheader();w.writerows(notas)
    hash_antes = rf.sha256(fonte)
    hash_csv_antes = rf.sha256(csvfile)
    relatorio=rf.executar(tmp_path,CATALOG)
    assert relatorio["representacoes"]==8
    assert relatorio["registros"]==80
    assert relatorio["es_kafka_modificados"] is False
    assert rf.sha256(fonte) == hash_antes
    assert rf.sha256(csvfile) == hash_csv_antes
    saida=tmp_path / relatorio["derivado"]
    html=tmp_path / relatorio["galeria"]
    assert saida.is_file() and html.is_file()
    assert "Questão 32" in html.read_text(encoding="utf-8")
    assert len(rf.ler_jsonl(saida))==80
