import json,csv
from pathlib import Path
from scripts.consolidar_auditoria_a3 import limpar_rascunho,processar

def test_rascunho_final_remove():
    assert limpar_rascunho('Texto a) b)\nRASCUNHO\n1\n2\n3\n4\n5\n')=='Texto a) b)'

def test_rascunho_nao_remove_trecho_sem_sequencia():
    assert limpar_rascunho('Texto\nRASCUNHO\n1\n2\n4\n5\n6\n') is None

def test_rascunho_nao_remove_texto_real_apos():
    assert limpar_rascunho('Texto\nRASCUNHO\n1\n2\n3\n4\n5\nOutra parte') is None

def test_consolidacao_preserva_amostra_e_lote(tmp_path):
    base=tmp_path; (base/'data/extraidos').mkdir(parents=True);(base/'evidencias').mkdir()
    qs=[];rows=[]
    for i in range(80):
        tipo='discursiva' if i in (2,10) else 'objetiva'
        q={'id':f'id{i}','tipo_questao':tipo,'numero_questao':i,'enunciado':'Texto\nRASCUNHO\n1\n2\n3\n4\n5\n' if i in (2,10) else f'Questao {i}', 'alertas':[]}
        qs.append(q)
        if i<50:
            errado=i in (2,10,11,13,21,24,26,28,32,48)
            rows.append({'id':q['id'],'ano':'2023','curso':'Agronomia','pagina':'1','tipo':tipo,
              'enunciado_correto_1_ou_0':'0' if errado else '1','alternativas_corretas_1_ou_0':'' if tipo=='discursiva' else '1','tipo_correto_1_ou_0':'1',
              'observacoes':'RASCUNHO' if tipo=='discursiva' else ('grafico' if errado else '')})
    dest=base/'data/extraidos/questoes_com_midias.jsonl'
    dest.write_text(''.join(json.dumps(q)+'\n' for q in qs))
    path=base/'evidencias/A3_revisao_manual.csv'
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    original=dest.read_bytes();csv_orig=path.read_bytes()
    result=processar(base,True)
    assert result['metricas']['alternativas']=={'aprovados':48,'avaliados':48,'nao_aplicavel':2}
    assert result['rascunhos_corrigidos_no_derivado']==2
    assert dest.read_bytes()==original and path.read_bytes()==csv_orig
    changed=[json.loads(s) for s in (base/result['derivado_criado']).read_text().splitlines()]
    assert all(changed[i]['enunciado']=='Texto' for i in (2,10))
    assert changed[1]==qs[1]

def test_resumo_denominadores(tmp_path):
    from scripts.resumir_revisao_a3 import resumir
    csvpath=tmp_path/'revisao.csv'
    rows=[]
    for i in range(50):
        tipo='discursiva' if i in (2,10) else 'objetiva'
        rows.append({'id':str(i),'tipo':tipo, 'enunciado_correto_1_ou_0':'0' if i<10 else '1',
         'alternativas_corretas_1_ou_0':'' if tipo=='discursiva' else '1', 'tipo_correto_1_ou_0':'1'})
    with csvpath.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    r=resumir(csvpath)
    assert r['enunciado']['percentual']==80
    assert r['alternativas']=={'corretos':48,'avaliados':48,'percentual':100.0,'nao_aplicavel':2}
