"""Decodificacao controlada de duas provas oficiais ENADE 2017.

O mapeamento foi derivado dos nomes dos glifos das fontes embutidas nos
PDFs oficiais fornecidos. Nao inclui arquivos de fontes nem usa OCR.
Ativar SOMENTE para os dois SHA-256 listados: outras provas podem usar
indices de glifo diferentes. Caractere nao identificado fica preservado.
"""
from __future__ import annotations

KNOWN_HASHES_2017 = {
    "c9ffd7b52f24f382f2546a2ee72d1331ad830fbee903e597888c512c32552518",  # Bacharelado
    "7ae440c22df812f9b28bcd3f746ea4ec1f836ad15dbe81ff468a883007f90348",  # Licenciatura
}

# Apenas glifos observados nos dois PDFs; o mapa nao e generalizavel.
FONT_MOJIBAKE_MAP = {
    '\x03': ' ',
    '\x04': 'A',
    '\x06': 'Á',
    '\x08': 'Ã',
    '\t': '\t',
    '\n': '\n',
    '\r': '\r',
    '\x11': 'B',
    '\x12': 'C',
    '\x18': 'D',
    '\x1a': 'F',
    '\x1c': 'E',
    '\x1e': 'É',
    ' ': ' ',
    '&': 'F',
    "'": 'G',
    ',': 'H',
    '/': 'I',
    '>': 'L',
    'D': 'M',
    'E': 'N',
    'K': 'O',
    'W': 'P',
    'Y': 'Q',
    'Z': 'R',
    '^': 'S',
    'd': 'T',
    'h': 'U',
    's': 'V',
    'Ă': 'a',
    'ă': 'à',
    'Ą': 'á',
    'ą': 'â',
    'Ć': 'ã',
    'ď': 'b',
    'Đ': 'c',
    'ĕ': 'ç',
    'Ě': 'd',
    'Ğ': 'e',
    'Ġ': 'é',
    'ġ': 'ê',
    'Ĩ': 'f',
    'Į': 'fi',
    'İ': 'fí',
    'Ň': 'fl',
    'Ő': 'g',
    'Ś': 'h',
    'ŝ': 'i',
    'ş': 'í',
    'ũ': 'j',
    'Ŭ': 'k',
    'ů': 'l',
    'ŵ': 'm',
    'Ŷ': 'n',
    'Ž': 'o',
    'ſ': 'ó',
    'ƀ': 'ô',
    'Ɓ': 'õ',
    'Ɖ': 'p',
    'Ƌ': 'q',
    'ƌ': 'r',
    'Ɛ': 's',
    'ƚ': 't',
    'Ɵ': 'ti',
    'ơ': 'tí',
    'Ʃ': 'tt',
    'Ƶ': 'u',
    'Ʒ': 'ú',
    'ǀ': 'v',
    'ǁ': 'w',
    'ǆ': 'x',
    'Ǉ': 'y',
    'ǌ': 'z',
    '͊': ':',
    '͍': '?',
    '͕': ',',
    '͖': ';',
    '͗': ':',
    '͘': '.',
    '͞': '“',
    '͟': '”',
    'ͬ': '/',
    'Ͳ': '-',
    'ͳ': '-',
    'ʹ': '–',
    '\u0378': '–',
    '\u0379': '–',
    'ͻ': '•',
    ';': '(',
    'Ϳ': ')',
    '\u0380': '[',
    'Ζ': 'Z',
    'Η': '"',
    'Θ': '&',
    'Σ': 'º',
    'Φ': '\x80',
    'Ψ': '$',
    'Ϭ': '0',
    'ϭ': '1',
    'Ϯ': '2',
    'ϯ': '3',
    'ϰ': '4',
    'ϱ': '5',
    'ϲ': '6',
    'ϳ': '7',
    'ϴ': '8',
    'ϵ': '9',
    'й': '%',
    'ф': '<',
    'х': '>',
    '⍻': '?',
}

def parece_codificado(texto: str) -> bool:
    return ('\x03' in texto or
            any(0 < ord(c) < 32 and c not in '\n\t\r' for c in texto) or
            any(255 < ord(c) < 0x800 for c in texto))

def decodificar_span(texto: str, fonte: str) -> str:
    if not fonte.startswith('Calibri') or not parece_codificado(texto):
        return texto
    return ''.join(FONT_MOJIBAKE_MAP.get(c, c) for c in texto)

def blocos_decodificados(pagina) -> list[tuple]:
    blocos = []
    for bloco in pagina.get_text('dict')['blocks']:
        if bloco.get('type') != 0:
            continue
        linhas = []
        for linha in bloco.get('lines', []):
            trechos = [decodificar_span(s['text'], s['font']) for s in linha.get('spans', [])]
            linhas.append(''.join(trechos))
        texto = '\n'.join(linhas)
        if not texto.strip():
            continue
        x0,y0,x1,y1 = bloco['bbox']
        blocos.append((x0,y0,x1,y1,texto,0,0))
    return blocos
