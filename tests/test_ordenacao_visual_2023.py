"""Regressões independentes do arquivo original: uso dos dois tipos de blocos."""
from pathlib import Path
import hashlib
import fitz
from enade_pipeline.extracao import parse_pdf, text_blocks


def test_grafico_nao_antecipa_enunciado(tmp_path: Path):
    f=tmp_path/'amostra.pdf'; d=fitz.open(); p=d.new_page(width=565,height=780)
    p.insert_text((30,80),'QUESTAO 03',fontsize=13)
    p.insert_text((30,110),'Estudos sobre cobertura vacinal de 2017 a 2021.',fontsize=11)
    for i in range(10):
        p.insert_text((40,200+i*25),str(60+i)+'.02',fontsize=9)
        p.insert_text((320,200+i*25),str(30+i)+'.09',fontsize=9)
    p.insert_text((30,500),'A) Item correto exemplo A.',fontsize=11)
    p.insert_text((30,525),'B) Item correto exemplo B.',fontsize=11)
    p.insert_text((30,550),'C) Item correto exemplo C.',fontsize=11)
    p.insert_text((30,575),'D) Item correto exemplo D.',fontsize=11)
    p.insert_text((30,600),'E) Item correto exemplo E.',fontsize=11)
    p.insert_text((30,744),'VALIDINEP2023'*4,fontsize=3)
    d.save(f);d.close()
    qs, _=parse_pdf(f,ano=2023,curso='Teste',pdf_url='https://download.inep.gov.br/teste.pdf',pdf_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    assert len(qs)==1
    assert qs[0]['enunciado'].startswith('Estudos sobre cobertura vacinal')
    assert len(qs[0]['alternativas'])==5
    assert 'VALIDINEP' not in str(qs[0])


def test_marca_embutida_na_alternativa_vai_para_higienizacao(tmp_path: Path):
    f=tmp_path/'teste.pdf';d=fitz.open();p=d.new_page()
    p.insert_text((30,95),'QUESTAO 01')
    p.insert_text((30,125),'Escolha a alternativa com o item de texto apropriado.')
    for i,c in enumerate('ABCDE'):
        tail=' VALIDINEP2023' if c=='E' else ''
        p.insert_text((30,170+i*30),f'{c}) Um item correto de exemplo {c}.{tail}')
    d.save(f);d.close()
    qs,_=parse_pdf(f,ano=2023,curso='Teste',pdf_url='https://download.inep.gov.br/teste.pdf',pdf_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    assert len(qs)==1
    assert 'VALIDINEP2023' in qs[0]['alternativas'][-1]['texto']
