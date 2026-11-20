"""Teste seguro da nova consolidacao de 280 registros (sem Kafka/Elasticsearch real)."""
from __future__ import annotations

import csv
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest

from scripts import indexar_v4_rf04 as v4
from scripts import estruturar_semantica_rf04 as rf04


def save_jsonl(file: Path, docs):
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in docs),encoding='utf-8')


def valid_item(y, n, *, id_=None, curso='Outros', tipo='objetiva'):
    return {'id': id_ or hashlib.sha256(f'{y}:{n}'.encode()).hexdigest(),
            'ano':y,'area':'Area', 'curso':curso, 'tipo_formacao':'FG',
            'numero_questao':(n%40)+1,'tipo_questao':tipo,
            'enunciado':'Texto da questao',
            'alternativas': [] if tipo=='discursiva' else [{'letra':'A','texto':'Exemplo'}],
            'pendente_revisao':True,'alertas':[],
            'origem':{'pdf_url':'https://example.org/pdf.pdf','pdf_sha256':'a'*64,
                      'pagina_inicial':1,'pagina_final':1}}


def dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(v4,'APROVACAO',tmp_path/'evidencias/aprovacao.json')
    monkeypatch.setattr(v4,'PREFLIGHT',tmp_path/'evidencias/preflight.json')
    dic = rf04.transcricoes_validas(json.loads(rf04.TRANSCRICOES.read_text(encoding='utf-8')))
    keys = sorted(rf04.CHAVES)
    orig=[]
    for idx,k in enumerate(keys):
        id_=rf04.IDS_PREFIXO[k]+'0'*(64-len(rf04.IDS_PREFIXO[k]))
        q=valid_item(2023,idx,id_=id_,curso=k[0]);q['numero_questao']=k[1]
        orig.append(q)
    for j in range(72):
        tipo='discursiva' if j<2 else 'objetiva'
        item=valid_item(2023,j+8,curso='Outro curso',tipo=tipo)
        if tipo=='discursiva':item['enunciado']+='\nRASCUNHO\n1\n2\n3\n4\n5\n'
        orig.append(item)
    clean=deepcopy(orig)
    for q in clean:
        if q['tipo_questao']=='discursiva':
            q['enunciado']=v4.limpar_rascunho(q['enunciado'])
            q['alertas'].append('rascunho_removido_em_derivado_pendente_revisao')
    notes=[]
    for i,q in enumerate(orig):
        notes.append({'id':q['id'],'ano':'2023','tipo':q['tipo_questao'],
            'enunciado_correto_1_ou_0':'0' if i<8 or q['tipo_questao']=='discursiva' else '1',
            'alternativas_corretas_1_ou_0':'1' if q['tipo_questao']=='objetiva' else '',
            'tipo_correto_1_ou_0':'1'})
    notes=notes[:50]
    vis=deepcopy(clean)
    for i,k in enumerate(keys):
        q=vis[i]
        n=6 if k==('Arquitetura e Urbanismo',11) else 2 if k==('Arquitetura e Urbanismo',17) else 1
        refs=[]
        for x in range(n):
            nome=f'data/midias/{i}_{x}.png';p=tmp_path/nome
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(f'imagem-{i}-{x}'.encode())
            ref={'arquivo':nome,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'descricao':'Pagina'}
            if k==('Arquitetura e Urbanismo',11) and x:
                ref['letra']='ABCDE'[x-1]
            refs.append(ref)
        q['apresentacao_visual_rf04']={'referencias':refs,'auditoria_original':'enunciado_reprovado'}
    sem, _=rf04.montar(vis,notes,dic,tmp_path)
    old=[valid_item(2017,i) for i in range(80)]+[valid_item(2021,i) for i in range(120)]
    save_jsonl(tmp_path/v4.ORIGINAL_2023,orig)
    save_jsonl(tmp_path/v4.FONTE_2023_CLEAN,clean)
    save_jsonl(tmp_path/v4.FONTE_2023,sem)
    save_jsonl(tmp_path/v4.FONTE_ANTIGA,old)
    csvpath=tmp_path/v4.CSV;csvpath.parent.mkdir(parents=True,exist_ok=True)
    with csvpath.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(notes[0]));w.writeheader();w.writerows(notes)
    return orig,clean,sem,old


def test_registro_aprovacao_e_preflight(tmp_path,monkeypatch):
    orig,clean,sem,old=dataset(tmp_path,monkeypatch)
    fontes=[tmp_path/p for p in (v4.ORIGINAL_2023,v4.FONTE_2023_CLEAN,v4.FONTE_2023,v4.FONTE_ANTIGA,v4.CSV)]
    hashes=[v4.v3.sha_file(p) for p in fontes]
    with pytest.raises(ValueError,match='Falta evidencia'):
        v4.preparar(tmp_path)
    with pytest.raises(ValueError,match='exatamente'):
        v4.registrar_aprovacao(tmp_path,'aprovadas')
    evidence=v4.registrar_aprovacao(tmp_path,v4.FRASE)
    assert evidence['resultado']=='APROVADO_PELO_REVISOR_EM_NOVA_CONFERENCIA'
    items,report=v4.preparar(tmp_path,persist=True)
    assert len(items)==280 and len(set(x['id'] for x in items))==280
    assert report['por_ano']=={'2017':80,'2021':120,'2023':80}
    assert report['representacoes_semanticas_aprovadas']==8
    assert report['rascunhos_discursivos_limpos']==2
    assert sum('semantica_rf04' in q for q in items)==8
    assert all(q['status_validacao']=='nao_revisada' and q['revisado_humanamente'] is False for q in items)
    assert all(q['semantica_rf04']['estado']=='APROVADA_EM_NOVA_CONFERENCIA_HUMANA' for q in items if 'semantica_rf04' in q)
    assert [v4.v3.sha_file(p) for p in fontes]==hashes
    assert v4.registrar_aprovacao(tmp_path,v4.FRASE)==evidence


def test_adulteracao_semantica_rejeitada(tmp_path,monkeypatch):
    dataset(tmp_path,monkeypatch)
    f=tmp_path/v4.FONTE_2023
    data=v4.v3.read_jsonl(f)
    data[0]['semantica_rf04']['linhas'][0][0]='VALOR ALTERADO'
    save_jsonl(f,data)
    with pytest.raises(ValueError,match='Dados semanticamente alterados'):
        v4.preparar_fontes(tmp_path)


def test_alteracao_original_rejeitada(tmp_path,monkeypatch):
    dataset(tmp_path,monkeypatch)
    f=tmp_path/v4.FONTE_2023_CLEAN
    data=v4.v3.read_jsonl(f)
    data[10]['enunciado']='ALTERADO'
    save_jsonl(f,data)
    with pytest.raises(ValueError,match='Enunciado fora'):
        v4.preparar_fontes(tmp_path)


def test_hash_imagem_rejeitado(tmp_path,monkeypatch):
    _,_,sem,_=dataset(tmp_path,monkeypatch)
    raw=sem[0]['semantica_rf04']['imagens'][0]['arquivo']
    (tmp_path/raw).write_bytes(b'ERRO')
    with pytest.raises(ValueError,match='SHA-256'):
        v4.preparar_fontes(tmp_path)


def test_mapping_referencias_preservadas():
    mapa=v4.mapa_v4()
    props=mapa['mappings']['properties']
    assert props['semantica_rf04']['enabled'] is False
    assert props['apresentacao_visual_rf04']['enabled'] is False
    assert props['rf04_aprovacao_status']['type']=='keyword'


def test_indice_v4_com_dados_estranhos_recusado():
    class I:
        def exists(self,index):return True
        def refresh(self,index):pass
    class FakeES:
        indices=I()
        def count(self,index):return {'count':1}
        def mget(self,index,body):return {'docs':[{'_id':i,'found':False} for i in body['ids']]}
    with pytest.raises(ValueError,match='desconhecidos'):
        v4.compara_indice(FakeES(),[{'id':hashlib.sha256(str(i).encode()).hexdigest()} for i in range(280)])


def test_indice_v4_idempotente_sem_divergencia():
    entradas=[{'id':hashlib.sha256(str(i).encode()).hexdigest(),'valor':i} for i in range(280)]
    class I:
        def exists(self,index):return True
        def refresh(self,index):pass
    class FakeES:
        indices=I()
        def count(self,index):return {'count':280}
        def mget(self,index,body):
            d={x['id']:x for x in entradas}
            return {'docs':[{'_id':i,'found':True,'_source':d[i]} for i in body['ids']]}
    r=v4.compara_indice(FakeES(),entradas)
    assert r['faltantes']==0 and r['presentes']==280 and r['contagem']==280


def test_snapshot_deterministico_indice_antigo():
    dados=[{'_id':'id2','_source':{'x':1}}, {'_id':'id1','_source':{'x':2}}]
    class I:
        def exists(self,index):return True
    class FakeES:
        indices=I()
        def count(self,index):return {'count':len(dados)}
        def search(self,index,query,size):return {'hits':{'hits':list(reversed(dados))}}
    a=v4.snapshot(FakeES(),'enade-questoes-v3')
    dados.reverse()
    b=v4.snapshot(FakeES(),'enade-questoes-v3')
    assert a==b and a['count']==2
