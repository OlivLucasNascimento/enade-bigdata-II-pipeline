#!/usr/bin/env python3
"""Critérios técnicos auditáveis; nunca preenche avaliação manual 0/1."""
from __future__ import annotations
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSONL = ROOT / 'data/extraidos/questoes.jsonl'
EVID = ROOT / 'evidencias'


def main() -> int:
    qs = [json.loads(s) for s in JSONL.read_text(encoding='utf-8').splitlines() if s.strip()]
    problems = []
    for q in qs:
        fields = [q.get('enunciado') or ''] + [a.get('texto') or '' for a in q.get('alternativas', [])]
        reasons = []
        if re.search('VALIDIN', ' '.join(fields), re.IGNORECASE):
            reasons.append('marca_validin_residual')
        if len(q.get('enunciado') or '') < 50:
            reasons.append('enunciado_curto')
        if q.get('tipo_questao') == 'objetiva' and len(q.get('alternativas', [])) != 5:
            reasons.append('alternativas_ausentes_ou_graficas')
        if any(not (a.get('texto') or '').strip() for a in q.get('alternativas', [])):
            reasons.append('alternativa_vazia')
        if reasons:
            problems.append({'id': q.get('id'), 'curso': q.get('curso'),
                             'numero_questao': q.get('numero_questao'),
                             'tipo_questao': q.get('tipo_questao'),
                             'pagina': q.get('origem', {}).get('pagina_inicial'),
                             'motivos': ','.join(reasons)})
    EVID.mkdir(parents=True, exist_ok=True)
    with (EVID / 'A3_pendencias_tecnicas.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=['id','curso','numero_questao','tipo_questao','pagina','motivos'])
        writer.writeheader(); writer.writerows(problems)
    summary = {
        'quantidade':len(qs), 'ids_unicos':len(set(q['id'] for q in qs)),
        'tipos':dict(Counter(q.get('tipo_questao') for q in qs)),
        'cursos':dict(Counter(q.get('curso') for q in qs)),
        'marcas_validin_restantes':sum('marca_validin_residual' in r['motivos'] for r in problems),
        'objetivas_sem_cinco_alternativas':sum('alternativas_ausentes_ou_graficas' in r['motivos'] for r in problems),
        'pendencias_tecnicas':len(problems),
        'revisao_humana_50_questoes':'PENDENTE',
        'status':'AUDITORIA_TECNICA_SEM_APROVACAO_EDITORIAL'
    }
    (EVID / 'A3_auditoria_ordenacao.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if summary['ids_unicos'] != summary['quantidade'] or summary['marcas_validin_restantes']:
        print('ERRO: inconsistência de IDs ou marcas de validação remanescentes')
        return 2
    print('Pendencias pontuais em A3_pendencias_tecnicas.csv; revisao humana continua pendente.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
