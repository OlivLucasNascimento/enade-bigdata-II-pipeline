#!/usr/bin/env python3
"""Compara o bruto e o higienizado, sem afirmar que a revisão humana foi feita."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enade_pipeline.higienizacao import contar_marcas


def carregar(p):
    return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    base = ROOT / 'data' / 'extraidos'
    bruto = carregar(base / 'questoes_brutas.jsonl')
    limpo = carregar(base / 'questoes.jsonl')
    registros = carregar(base / 'auditoria_marcas.jsonl')
    ids_b = [q['id'] for q in bruto]
    ids_l = [q['id'] for q in limpo]
    iguais = len(ids_b) == len(ids_l) and ids_b == ids_l
    rem = sum(q['marcas_removidas'] for q in registros)
    residuais = sum(contar_marcas(q) for q in limpo)
    resumo = {
        'registros_brutos':len(bruto), 'registros_higienizados':len(limpo),
        'ids_e_ordem_inalterados':iguais,
        'questoes_com_marca_no_bruto':sum(contar_marcas(q)>0 for q in bruto),
        'questoes_afetadas':len(registros),
        'marcas_removidas':rem, 'marcas_residuais_identificadas':residuais,
        'revisao_humana': 'PENDENTE',
        'status':'aprovado_tecnicamente_pendente_revisao_humana' if iguais and residuais==0 else 'falha'
    }
    evid = ROOT / 'evidencias' / 'A3_auditoria_higienizacao.json'
    evid.parent.mkdir(exist_ok=True)
    evid.write_text(json.dumps(resumo,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(resumo,indent=2,ensure_ascii=False))
    return 0 if iguais and residuais==0 else 2

if __name__ == '__main__':
    raise SystemExit(main())
