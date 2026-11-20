"""Leitura conservadora da tabela oficial de gabaritos ENADE 2023.

Vincula apenas pares QUESTÃO n -> A/B/C/D/E/ANULADA com alinhamento textual.
Não inventa gabarito para discursivas e sinaliza tabelas não interpretadas.
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz

PAIR_2017 = re.compile(r'^\s*(\d{1,2})\s+([A-E]|ANULADA)\s*$', re.I | re.M)

PAIR = re.compile(r'QUEST[ÃA]O\s+(?:(DISCURSIVA)\s+)?(\d{1,2})\s*(?:[:|\-]\s*)?(?:GABARITO\s+)?(ANULAD[AO]|[A-E]|\*\*\*)\s*$', re.I)


def parse_gabarito(path: Path) -> tuple[dict[tuple[str, int], dict], list[str]]:
    outcomes: dict[tuple[str, int], dict] = {}
    problems = []
    with fitz.open(path) as doc:
        # Gabaritos 2017 usam colunas ITEM / GABARITO (sem 'QUESTÃO').
        # Exigir 35 itens completos para evitar vinculação parcial ou incorreta.
        if any('GABARITO DEFINITIVO DAS QUESTÕES DE MÚLTIPLA ESCOLHA'
               in page.get_text('text') and 'ITEM' in page.get_text('text')
               for page in doc):
            candidatos = {}
            divergencias = []
            for page_no, page in enumerate(doc, 1):
                texto = page.get_text('text', sort=True)
                for numero_texto, letra in PAIR_2017.findall(texto):
                    numero = int(numero_texto)
                    if numero < 1 or numero > 35:
                        continue
                    chave = ('objetiva', numero)
                    resposta = letra.upper()
                    if chave in candidatos and candidatos[chave]['valor'] != resposta:
                        divergencias.append(numero)
                    candidatos[chave] = {'valor': resposta, 'pagina': page_no}
            faltantes = sorted(set(range(1, 36)) - {n for _, n in candidatos})
            if faltantes or divergencias:
                problems.append(f'Gabarito 2017 incompleto/inconsistente: faltam={faltantes}, conflitos={divergencias}')
                return {}, problems
            return candidatos, problems
        for page_no, page in enumerate(doc, 1):
            # Tabela de 2023 tem colunas Item/Gabarito alinhadas horizontalmente.
            # Agrupar palavras pela posição vertical funciona também quando o
            # PyMuPDF separa em blocos diferentes as duas colunas.
            words = sorted(page.get_text('words'), key=lambda z: (z[1], z[0]))
            rows: list[list] = []
            for word in words:
                for row in reversed(rows[-3:]):
                    if abs(row[0][1] - word[1]) < 4:
                        row.append(word)
                        break
                else:
                    rows.append([word])
            for row in rows:
                line = ' '.join(w[4] for w in sorted(row, key=lambda z: z[0]))
                m = PAIR.search(line.strip())
                if not m:
                    continue
                key = ('discursiva' if m.group(1) else 'objetiva', int(m.group(2)))
                answer = m.group(3).upper()
                answer = 'ANULADA' if answer.startswith('ANULAD') else answer
                if key in outcomes and outcomes[key]['valor'] != answer:
                    problems.append(f'Conflito de gabarito {key} na pagina {page_no}')
                    outcomes.pop(key, None)
                    continue
                outcomes[key] = {'valor': answer, 'pagina': page_no}
    if len(outcomes) < 5:
        problems.append(f'Gabarito reconhecido parcialmente: apenas {len(outcomes)} linhas; revisar PDF')
    return outcomes, problems
