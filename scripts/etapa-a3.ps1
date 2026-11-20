$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
Write-Host 'ETAPA A3 — Instalando bibliotecas e testando extração'
py -m pip install -r .\requirements-pipeline.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha na instalacao de dependencias A3' }
py -m pytest -q .\tests\test_extracao_a3.py .\tests\test_integracao_a4.py
if ($LASTEXITCODE -ne 0) { throw 'Testes unitarios A3/A4 falharam' }
py .\scripts\extrair_questoes.py --limite-provas 2 | Tee-Object -FilePath .\evidencias\A3_saida.txt
if ($LASTEXITCODE -ne 0) { throw 'Nenhuma questao extraida. Confira manifesto e pendencias.' }
py .\scripts\gerar_revisao_a3.py --amostra 50
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar CSV de revisao' }
Write-Host 'A3: JSONL de RASCUNHO extraido. Confira data/extraidos e evidencias/A3_resumo.json.'
