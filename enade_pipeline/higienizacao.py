"""Higienização conservadora de marcas de validação observadas em PDFs ENADE.

Preserva o JSONL bruto para auditoria e nunca considera um texto automaticamente revisado.
"""
from __future__ import annotations

from copy import deepcopy
import re

# A variação com "3" no lugar de "E" foi observada no texto extraído.
MARCA_ENADE = re.compile(r'VALIDIN(?:E|3)P2023', re.IGNORECASE)


def contar_marcas(questao: dict) -> int:
    """Contagem restrita aos campos textuais destinados a busca."""
    campos = [questao.get('enunciado'), questao.get('texto_base')]
    campos.extend(item.get('texto') for item in questao.get('alternativas', []) if isinstance(item, dict))
    return sum(len(MARCA_ENADE.findall(v)) for v in campos if isinstance(v, str))


def higienizar_questao(questao: dict) -> tuple[dict, dict | None]:
    """Remove SOMENTE os tokens exatos conhecidos e sinaliza revisão humana.

    Não altera o registro recebido: é obrigação da extração salvar o registro bruto.
    """
    limpa = deepcopy(questao)
    campos_atingidos: dict[str, int] = {}

    def tratar(texto: object, nome: str) -> object:
        if not isinstance(texto, str):
            return texto
        novo, n = MARCA_ENADE.subn('', texto)
        if n:
            campos_atingidos[nome] = n
            # Não normaliza o texto da questão além de retirar o marcador.
            return novo
        return texto

    for campo in ('enunciado', 'texto_base'):
        limpa[campo] = tratar(limpa.get(campo), campo)
    for i, alt in enumerate(limpa.get('alternativas', [])):
        if isinstance(alt, dict):
            alt['texto'] = tratar(alt.get('texto'), f'alternativas[{i}].texto')

    if not campos_atingidos:
        return limpa, None

    alertas = limpa.setdefault('alertas', [])
    if 'marca_validinep_removida_revisar' not in alertas:
        alertas.append('marca_validinep_removida_revisar')
    limpa['pendente_revisao'] = True
    origem = limpa.get('origem') or {}
    audit = {
        'id': limpa.get('id'), 'ano': limpa.get('ano'), 'curso': limpa.get('curso'),
        'numero_questao': limpa.get('numero_questao'), 'tipo_questao': limpa.get('tipo_questao'),
        'pdf_sha256': origem.get('pdf_sha256'), 'pagina_inicial': origem.get('pagina_inicial'),
        'pagina_final': origem.get('pagina_final'),
        'campos_atingidos': campos_atingidos,
        'marcas_removidas': sum(campos_atingidos.values()),
        'status': 'limpeza_automatica_pendente_revisao_humana'
    }
    return limpa, audit
