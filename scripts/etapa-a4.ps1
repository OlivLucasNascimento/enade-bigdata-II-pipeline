$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
Write-Host 'ETAPA A4 - Teste fim a fim Kafka para Elasticsearch (ambiente local sem Kerberos)'
$arquivo = '.\data\extraidos\questoes.jsonl'
if (!(Test-Path $arquivo)) { throw 'Execute a Etapa A3 primeiro: arquivo de questoes nao encontrado' }
if ((Get-Item $arquivo).Length -eq 0) { throw 'A3 gerou um arquivo vazio; interrompendo' }
docker compose ps
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose nao acessivel' }
py -m pytest -q .\tests\test_extracao_a3.py .\tests\test_integracao_a4.py
if ($LASTEXITCODE -ne 0) { throw 'Falha nos testes' }
py .\scripts\pipeline_a4.py criar-indice
if ($LASTEXITCODE -ne 0) { throw 'Indice Elastic falhou' }
py .\scripts\pipeline_a4.py publicar --limite 10
if ($LASTEXITCODE -ne 0) { throw 'Falha na publicacao' }
py .\scripts\pipeline_a4.py consumir --limite 10
if ($LASTEXITCODE -ne 0) { throw 'Falha ao consumir/indexar' }
py .\scripts\pipeline_a4.py verificar --minimo 1
if ($LASTEXITCODE -ne 0) { throw 'A4 incompleta: nenhum documento indexado' }
Write-Host 'A4 teste local concluido: salve a saida e valide com docs/ETAPAS_A3_A4_A5.md.'
