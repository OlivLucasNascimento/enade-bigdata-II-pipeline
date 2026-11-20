#!/usr/bin/env python3
"""Revisão humana das 50 questões: PDF original e extração lado a lado.

Interface local, SOMENTE 127.0.0.1. Não preenche notas automaticamente.
Grava no CSV existente com backup e gravação atômica. Python >= 3.10, PyMuPDF.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

FIELDS = ['id', 'curso', 'ano', 'pagina', 'tipo', 'previa',
          'enunciado_correto_1_ou_0', 'alternativas_corretas_1_ou_0',
          'tipo_correto_1_ou_0', 'observacoes']
EDIT = ('enunciado_correto_1_ou_0', 'alternativas_corretas_1_ou_0',
        'tipo_correto_1_ou_0', 'observacoes')
HTML = r'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/><title>ENADE · Revisão das 50 questões</title>
<style>
:root{font:15px system-ui,-apple-system,'Segoe UI',sans-serif;color:#183048;background:#f4f8fb}
*{box-sizing:border-box}body{margin:0}header{background:#102f46;color:white;padding:12px 18px;display:flex;gap:20px;align-items:center;flex-wrap:wrap}
header h1{font-size:19px;margin:0}#progress{margin-left:auto;font-weight:700}
main{display:grid;grid-template-columns:245px minmax(350px,1fr) minmax(340px,1fr);height:calc(100vh - 65px)}
nav{overflow:auto;background:white;border-right:1px solid #dae3ec;padding:8px}
nav button{display:block;text-align:left;width:100%;margin:4px 0;padding:9px;border-radius:6px;border:1px solid #dce5ec;background:#fff;cursor:pointer;font-size:12px}
nav button.active{background:#dff3ef;border-color:#1c8c7f}nav button.done:before{content:'✓ ';color:#087f5b}
#documento{overflow:auto;background:#e9eef2;padding:12px;border-right:1px solid #dae3ec}
#documento img{display:block;max-width:100%;width:100%;margin:auto;box-shadow:0 2px 10px #8888;background:white}
#detalhes{overflow:auto;padding:16px 20px;background:white}#detalhes h2{margin:0 0 8px;font-size:19px}
.pill{background:#e9f3f7;color:#254458;border-radius:15px;padding:3px 8px;font-size:12px}
.desc{font-size:13px;color:#627487}.part{white-space:pre-wrap;font:13px/1.5 'Segoe UI',system-ui,sans-serif;background:#f5f8fa;border:1px solid #dee8ef;padding:12px;border-radius:7px;max-height:270px;overflow:auto}
.alt{padding:8px 0;border-bottom:1px solid #edf1f4;font-size:13px;white-space:pre-wrap}
label{display:block;font-weight:650;margin-top:15px;font-size:14px}select,textarea{width:100%;padding:8px;border:1px solid #bdceda;border-radius:5px;margin:5px 0;background:white}textarea{height:85px;resize:vertical}
.action{background:#167769;color:white;border:0;border-radius:5px;padding:11px 14px;cursor:pointer;font-weight:700}.action:disabled{opacity:.5}.secondary{background:#e7eff6;color:#183048}.warn{background:#ffefda;color:#84510b;padding:10px;border-radius:5px;margin-top:10px;font-size:13px}
#imageNav{display:flex;gap:10px;align-items:center;justify-content:center;margin:0 0 12px;position:sticky;top:0;background:#e9eef2;padding:6px}
@media(max-width:1100px){main{grid-template-columns:170px 1fr;}#detalhes{grid-column:2;max-height:65vh}#documento{max-height:60vh}nav{grid-row:span 2}}
@media(max-width:680px){main{display:block;height:auto}nav{max-height:200px}#documento{max-height:80vh}#detalhes{max-height:none}}
</style></head><body><header><h1>ENADE · Auditoria das 50 questões</h1><span>PDF oficial × Extração JSONL</span><span id="progress">Carregando...</span></header>
<main><nav id="navegacao"></nav><section id="documento"><div id="imageNav"><button class="action secondary" onclick="pageDelta(-1)">← Página</button><strong id="pagina">Página —</strong><button class="action secondary" onclick="pageDelta(1)">Página →</button></div><img id="imagem" alt="Página do PDF original"/></section>
<section id="detalhes"><h2 id="titulo">Carregando</h2><span class="pill" id="subtitulo"></span><p class="desc">Avalie o que está no JSONL, comparando ao PDF à esquerda. Não marque aprovação sem conferir.</p><h3>Enunciado extraído</h3><div id="enunciado" class="part"></div><h3>Alternativas extraídas</h3><div id="alternativas"></div><div id="aviso"></div>
<label>Enunciado corresponde ao original?</label><select id="en" aria-label="Avaliação do enunciado"><option value="">— Pendente —</option><option value="1">1 · Correto</option><option value="0">0 · Incorreto / incompleto</option></select>
<label>Alternativas completas e corretas?</label><select id="al" aria-label="Avaliação das alternativas"><option value="">— Pendente / não se aplica —</option><option value="1">1 · Corretas</option><option value="0">0 · Incorretas / incompletas</option></select>
<label>Tipo de questão correto?</label><select id="tipo" aria-label="Avaliação do tipo"><option value="">— Pendente —</option><option value="1">1 · Correto</option><option value="0">0 · Incorreto</option></select>
<label>Observações / imagens ausentes / erros</label><textarea id="obs" placeholder="Ex.: imagem indispensável; questão 11, alternativas gráficas não transcritas"></textarea>
<div style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0"><button class="action" onclick="salvar()" id="salvar">Salvar avaliação</button><button class="action secondary" onclick="mover(1)">Salvar e próxima →</button></div><div id="status" class="desc"></div>
</section></main><script>
let rows=[], idx=0, numPagina=1;const $=id=>document.getElementById(id);
function esc(s){return String(s??'')}
async function init(){const j=await (await fetch('/api/data')).json();rows=j.rows;refrescarMenu();mostrar(0)}
function completo(r){return ['0','1'].includes(r.enunciado_correto_1_ou_0)&&['0','1'].includes(r.tipo_correto_1_ou_0)&&(r.tipo==='discursiva'||['0','1'].includes(r.alternativas_corretas_1_ou_0))}
function refrescarMenu(){const nav=$('navegacao');nav.replaceChildren();rows.forEach((r,i)=>{let b=document.createElement('button');b.className=(i===idx?'active ':'')+(completo(r)?'done':'');b.textContent=`${String(i+1).padStart(2,'0')} · ${r.curso==='Agronomia'?'AGR':'ARQ'} · ${r.tipo==='discursiva'?'D':'Q'}${r.numero_questao} · p.${r.pagina}`;b.onclick=()=>mostrar(i);nav.append(b)});$('progress').textContent=`${rows.filter(completo).length} / ${rows.length} conferidas`}
function mostrar(i){if(i<0||i>=rows.length)return;idx=i;let r=rows[i];numPagina=r.pagina;
$('titulo').textContent=`${i+1}/50 · ${r.curso} · ${r.tipo==='discursiva'?'Discursiva':'Questão'} ${r.numero_questao}`;
$('subtitulo').textContent=`Ano ${r.ano} • página ${r.pagina} • ID ${r.id.slice(0,12)}`;
$('enunciado').textContent=esc(r.enunciado);let box=$('alternativas');box.replaceChildren();if(!r.alternativas.length)box.textContent='Sem alternativas textuais extraídas.';
(r.alternativas||[]).forEach(a=>{let d=document.createElement('div');d.className='alt';d.textContent=`${a.letra}) ${a.texto}`;box.append(d)});
$('en').value=r.enunciado_correto_1_ou_0||'';$('al').value=r.alternativas_corretas_1_ou_0||'';$('tipo').value=r.tipo_correto_1_ou_0||'';$('obs').value=r.observacoes||'';
$('al').disabled=r.tipo==='discursiva';let w=[];if(r.tipo==='objetiva'&&r.alternativas.length!==5)w.push(`Foram extraídas ${r.alternativas.length} alternativas; verifique o PDF e as referências gráficas.`);
if((r.alertas||[]).includes('figuras_para_conferencia_visual'))w.push('Há elementos visuais associados: confira o PDF.');
$('aviso').replaceChildren();if(w.length){let a=document.createElement('div');a.className='warn';a.textContent=w.join(' ');$('aviso').append(a)}$('status').textContent='';imagem();refrescarMenu()}
function imagem(){let r=rows[idx];$('pagina').textContent=`Página ${numPagina}`;$('imagem').src=`/api/page?id=${encodeURIComponent(r.id)}&p=${numPagina}`}
function pageDelta(n){numPagina=Math.max(1,numPagina+n);imagem()}
async function salvar(){let r=rows[idx];let data={id:r.id,enunciado_correto_1_ou_0:$('en').value,alternativas_corretas_1_ou_0:r.tipo==='discursiva'?'':$('al').value,tipo_correto_1_ou_0:$('tipo').value,observacoes:$('obs').value};
$('salvar').disabled=true;try{let res=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});let x=await res.json();if(!res.ok)throw new Error(x.error||'Erro');Object.assign(r,data);$('status').textContent='✓ Avaliação salva em evidencias/A3_revisao_manual.csv';refrescarMenu();return true}catch(e){$('status').textContent='ERRO ao salvar: '+e.message;return false}finally{$('salvar').disabled=false}}
async function mover(n){if(await salvar())mostrar(Math.min(rows.length-1,idx+n))}
init().catch(e=>{$('titulo').textContent='Erro: '+e.message});
</script></body></html>'''


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

class Review:
    def __init__(self, base: Path):
        self.base=base.resolve()
        self.csv=self.base/'evidencias'/'A3_revisao_manual.csv'
        self.jsonl=self.base/'data'/'extraidos'/'questoes_com_midias.jsonl'
        if not self.jsonl.exists():
            self.jsonl=self.base/'data'/'extraidos'/'questoes.jsonl'
        self.raw=self.base/'data'/'raw'
        if not self.csv.exists() or not self.jsonl.exists() or not self.raw.exists():
            raise FileNotFoundError('Faltam evidencias/A3_revisao_manual.csv, JSONL ou data/raw')
        self.rows=self.read_csv()
        self.qs={q['id']:q for q in (json.loads(s) for s in self.jsonl.read_text(encoding='utf-8').splitlines() if s.strip())}
        if len(self.rows)!=50 or len({r['id'] for r in self.rows})!=50 or any(r['id'] not in self.qs for r in self.rows):
            raise ValueError('A amostra precisa conter 50 IDs únicos presentes no JSONL')
        self.pdfs={}; self.paths={}
        for q in self.qs.values():
            h=q['origem']['pdf_sha256'].lower()
            if h in self.pdfs:continue
            matches=[p for p in self.raw.rglob('*.pdf') if q['curso'].casefold().split(' ')[0] in p.name.casefold()]
            correct=next((p for p in matches if sha256(p).lower()==h),None)
            if not correct:
                # Provas de arquivo diferente: busca por hash no acervo local apenas.
                correct=next((p for p in self.raw.rglob('*.pdf') if sha256(p).lower()==h),None)
            if not correct:raise FileNotFoundError(f'PDF original não localizado, SHA-256 {h[:12]}')
            self.pdfs[h]=pymupdf.open(correct);self.paths[h]=correct
        self.backup()
    def read_csv(self):
        with self.csv.open('r',encoding='utf-8-sig',newline='') as f:
            rd=csv.DictReader(f); rows=list(rd)
            if not set(FIELDS).issubset(rd.fieldnames or []):raise ValueError('Colunas CSV incorretas')
        return rows
    def backup(self):
        p=self.csv.parent/f'A3_revisao_manual_antes_da_sessao_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        shutil.copy2(self.csv,p);print('Backup da revisão:',p.relative_to(self.base))
    def overview(self):
        values=[]
        for r in self.rows:
            q=self.qs[r['id']]
            values.append({**r,'numero_questao':q['numero_questao'],'enunciado':q['enunciado'],
                           'alternativas':q['alternativas'],'alertas':q.get('alertas',[])})
        return {'rows':values}
    def save(self, data):
        if not isinstance(data,dict):raise ValueError('JSON inválido')
        id_=data.get('id');r=next((x for x in self.rows if x['id']==id_),None)
        if r is None:raise ValueError('ID fora da amostra')
        for k in EDIT[:3]:
            if data.get(k,'') not in ('','0','1'):raise ValueError('Avaliação aceita apenas 0, 1 ou pendente')
        obs=data.get('observacoes','')
        if not isinstance(obs,str) or len(obs)>3000:raise ValueError('Observação inválida')
        for k in EDIT:r[k]=data.get(k,'')
        if r['tipo']=='discursiva':r['alternativas_corretas_1_ou_0']=''
        # Salva csv no formato original, usando replace atômico; nunca altera o JSONL/PDF.
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8-sig',newline='',delete=False,dir=self.csv.parent,suffix='.tmp') as f:
            out=f.name;w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore');w.writeheader();w.writerows(self.rows)
        os.replace(out,self.csv)
    def image(self,id_:str,page:int):
        q=self.qs.get(id_)
        if q is None or not any(r['id']==id_ for r in self.rows):raise ValueError('ID fora da amostra')
        doc=self.pdfs[q['origem']['pdf_sha256'].lower()]
        if page<1 or page>doc.page_count:raise ValueError('Página inexistente')
        pix=doc[page-1].get_pixmap(dpi=120,alpha=False)
        return pix.tobytes('png')


def serve(base:Path,port:int):
    review=Review(base)
    class Handler(BaseHTTPRequestHandler):
        def _send(self,status:int,mime:str,body:bytes):
            self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def _json(self,status:int,payload):self._send(status,'application/json; charset=utf-8',json.dumps(payload,ensure_ascii=False).encode('utf-8'))
        def do_GET(self):
            path=urlparse(self.path)
            try:
                if path.path=='/':return self._send(200,'text/html; charset=utf-8',HTML.encode('utf8'))
                if path.path=='/api/data':return self._json(200,review.overview())
                if path.path=='/api/page':
                    qs=parse_qs(path.query);id_=qs.get('id',[''])[0];p=int(qs.get('p',['0'])[0]);
                    return self._send(200,'image/png',review.image(id_,p))
                return self._json(404,{'error':'Rota não encontrada'})
            except (ValueError,KeyError) as e:return self._json(400,{'error':str(e)})
        def do_POST(self):
            if urlparse(self.path).path!='/api/save':return self._json(404,{'error':'Rota não encontrada'})
            if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':return self._json(415,{'error':'Requer JSON'})
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{port}',f'http://localhost:{port}'):
                return self._json(403,{'error':'Origem não autorizada'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n>10000 or n<=0:raise ValueError('Payload inválido')
                data=json.loads(self.rfile.read(n));review.save(data);return self._json(200,{'ok':True})
            except (ValueError,KeyError,json.JSONDecodeError) as e:return self._json(400,{'error':str(e)})
        def log_message(self,format,*args):pass
    srv=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Abra no navegador: http://127.0.0.1:{port}\nFeche com Ctrl+C.')
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--porta',type=int,default=8765)
    a=parser.parse_args(argv);serve(a.base,a.porta)
if __name__=='__main__':main()
