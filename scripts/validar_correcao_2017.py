#!/usr/bin/env python3
"""Reextrai de forma nao destrutiva o lote prioritario ENADE 2017/2021.

Nao mexe nos indice Elasticsearch, Kafka, Redis ou dados de 2023.
Exige as cinco provas e os 35 itens dos dois gabaritos 2017.
"""
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from enade_pipeline.extracao import extrair_manifesto


def ler_jsonl(path: Path):
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    manifesto = ROOT / 'data/manifests/catalogo_prioritarios_2017_2021.csv'
    anterior = ROOT / 'data/extraidos_2017_2021/questoes.jsonl'
    novo = ROOT / 'data/extraidos_2017_2021_corrigidos'
    evidencia = ROOT / 'evidencias/A3_validacao_correcao_2017.json'
    if not manifesto.is_file():
        raise SystemExit(f'Manifesto nao encontrado: {manifesto}')
    # Salvar hash/IDs do lote antigo antes de gerar novo lote independente.
    antigos = ler_jsonl(anterior)
    resumo = extrair_manifesto(manifesto, ROOT, novo, max_provas=0)
    questoes = ler_jsonl(novo / 'questoes.jsonl')
    contagem = Counter((int(q['ano']), q['curso'], q['tipo_questao']) for q in questoes)
    contagem_2017 = {}
    problemas = []
    for curso in ('Ciência da Computação – Bacharelado', 'Ciência da Computação – Licenciatura'):
        grupo = [q for q in questoes if int(q['ano']) == 2017 and q['curso'] == curso]
        obj = [q for q in grupo if q['tipo_questao'] == 'objetiva']
        disc = [q for q in grupo if q['tipo_questao'] == 'discursiva']
        numeros_obj = sorted(q['numero_questao'] for q in obj)
        numeros_disc = sorted(q['numero_questao'] for q in disc)
        respostas = sum(q.get('gabarito') in ('A','B','C','D','E') or q.get('anulada') for q in obj)
        contagem_2017[curso] = {'objetivas': len(obj), 'discursivas': len(disc),
                               'numeros_objetivas': numeros_obj, 'numeros_discursivas': numeros_disc,
                               'gabaritos_vinculados': respostas,
                               'alternativas_textuais_completas': sum(len(q['alternativas']) == 5 for q in obj),
                               'questoes_com_alternativas_graficas': [q['numero_questao'] for q in obj if 'alternativas_exclusivamente_graficas_pdf_2017' in q.get('alertas',[])]}
        if numeros_obj != list(range(1, 36)):
            problemas.append(f'{curso}: numeracao objetiva incompleta')
        if numeros_disc != [1,2,3,4,5]:
            problemas.append(f'{curso}: numeracao discursiva incompleta')
        if respostas != 35:
            problemas.append(f'{curso}: gabaritos vinculados {respostas}/35 (nao aprovar)')
        if sum(len(q.get('alternativas', [])) == 5 for q in obj) != 34:
            problemas.append(f'{curso}: alternativas textuais inesperadas')
    antigos_ids = {q['id'] for q in antigos}
    novos_ids = {q['id'] for q in questoes}
    if not antigos_ids.issubset(novos_ids):
        problemas.append(f'{len(antigos_ids - novos_ids)} IDs do lote anterior nao preservados')
    if len(questoes) != 200 or len(novos_ids) != 200:
        problemas.append(f'Esperados 200 registros e IDs unicos; obtidos={len(questoes)} ids={len(novos_ids)}')
    saida = {
        'status': 'OK_RASCUNHO_TECNICO' if not problemas else 'PENDENTE_NAO_APROVADO',
        'total_anterior': len(antigos), 'total_novo': len(questoes),
        'ids_anteriores_preservados': antigos_ids.issubset(novos_ids),
        'novas_questoes': len(novos_ids - antigos_ids),
        'cursos_2017': contagem_2017,
        'pendencias_pdf': resumo['pendencias_pdf'],
        'falhas': problemas,
        'revisao_humana': 'PENDENTE',
        'limitacoes': ['Correcao de fonte aplica-se somente a dois hashes oficiais de 2017',
                       'Questao 9 tem alternativas graficas, nao texto convertido',
                       'Graficos, formulas, tabelas e textos de fontes secundarias dependem de revisao visual',
                       'Nenhum indice Kafka/Elasticsearch foi atualizado'],
        'saida': str((novo / 'questoes.jsonl').relative_to(ROOT)),
    }
    evidencia.parent.mkdir(parents=True, exist_ok=True)
    evidencia.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    if problemas:
        raise SystemExit('Falha na conferencia. Lote anterior preservado; NAO indexar este lote.')

if __name__ == '__main__':
    main()
