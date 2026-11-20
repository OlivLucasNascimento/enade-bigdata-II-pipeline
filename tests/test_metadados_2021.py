import importlib.util
import sys
import types
from pathlib import Path

def load(nome):
    if nome == 'coletar_enade.py' and 'truststore' not in sys.modules:
        sys.modules['truststore'] = types.SimpleNamespace(inject_into_ssl=lambda: None)
    base = Path(__file__).resolve().parents[1] / 'scripts' / nome
    spec = importlib.util.spec_from_file_location(base.stem, base)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_paragrafos_2021_identificados_como_cursos():
    c=load('coletar_enade.py')
    html='''<html><article><p>Artes visuais (licenciatura)</p><ul>
    <li><a href="https://download.inep.gov.br/enade/provas_e_gabaritos/2021_PV_licenciatura_artes_visuais.pdf">Prova</a></li>
    <li><a href="https://download.inep.gov.br/enade/provas_e_gabaritos/2021_GB_licenciatura_artes_visuais.pdf">Gabarito</a></li>
    <li><a href="https://download.inep.gov.br/enade/padrao_resposta/2021_artes_visuais.pdf">Padrão de resposta</a></li></ul>
    <p>Ciência da computação (bacharelado)</p><a href="https://download.inep.gov.br/enade/provas_e_gabaritos/2021_PV_bacharelado_ciencia_computacao.pdf">Prova</a></article></html>'''
    dados=c.parse_year_page(html,c.BASE+'/2021',2021)
    assert [x['curso'] for x in dados]==['Artes visuais (licenciatura)']*3+['Ciência da computação (bacharelado)']


def test_reparacao_preserva_hashes_e_urls():
    c=load('corrigir_cursos_2021.py')
    linhas=[]
    for n, curso in enumerate(c.CURSOS_2021):
        for tipo in c.TIPOS:
            # Testa apenas formato; nenhum hash/URL deve ser modificado.
            stem='abc'+str(n)
            arq={'prova':'2021_PV_'+stem,'gabarito':'2021_GB_'+stem,'padrao_resposta':'2021_'+stem}[tipo]
            linhas.append(dict(ano='2021',curso='nao_identificado',tipo=tipo,url=f'https://download.inep.gov.br/{arq}.pdf',sha256='f'*64,arquivo='data/raw/existente.pdf',status='existente'))
    hashes=[x['sha256'] for x in linhas]; orig=[x['url'] for x in linhas]
    assert c.validar_e_corrigir(linhas)==90
    assert [r['sha256'] for r in linhas]==hashes
    assert [r['url'] for r in linhas]==orig
    assert all(r['curso']!='nao_identificado' for r in linhas)


def test_erro_antes_de_modificar():
    c=load('corrigir_cursos_2021.py')
    linhas=[]
    for n, curso in enumerate(c.CURSOS_2021):
        for tipo in c.TIPOS:
            stem='abc'+str(n)
            arq={'prova':'2021_PV_'+stem,'gabarito':'2021_GB_'+stem,'padrao_resposta':'2021_'+stem}[tipo]
            linhas.append(dict(ano='2021',curso='nao_identificado',tipo=tipo,url=f'https://download.inep.gov.br/{arq}.pdf'))
    linhas[4]['tipo']='prova'
    try: c.validar_e_corrigir(linhas)
    except ValueError: pass
    else: raise AssertionError('Deveria interromper por ordem inesperada')
    assert all(x['curso']=='nao_identificado' for x in linhas)
